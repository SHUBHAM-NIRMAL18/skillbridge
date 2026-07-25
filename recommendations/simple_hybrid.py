from __future__ import annotations
from typing import List, Dict, Tuple, Iterable, Optional
from collections import defaultdict
from dataclasses import dataclass
from math import exp, sqrt
import re

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .skill_normalization import SKILL_SYNONYMS

#VERSION = "1.0.0"  # version of this module
EVENT_WEIGHTS = {"view": 1.0, "save": 3.0, "apply": 6.0, "dismiss": -2.0}
DECAY_LAMBDA = 0.02         # ~35-day half-life
WINDOW_DAYS = 90            # collaborative lookback


# ——————————————————————————————————————————
# Lazy model getters (adjust app labels if different)
# ——————————————————————————————————————————
JobPost = lambda: apps.get_model("company", "JobPost")
InternshipPost = lambda: apps.get_model("company", "InternshipPost")
Profile = lambda: apps.get_model("candidate", "Profile")
Experience = lambda: apps.get_model("candidate", "Experience")

# Optional: if you already have an events table, wire it here (else we’ll just skip CF)
def _candidate_event_model():
    # Try to find a model named CandidateEvent if you created one; else return None
    try:
        return apps.get_model("recommendations", "CandidateEvent")
    except Exception:
        return None


_HTML = re.compile(r"<[^>]+>")

def _clean_text(s: str) -> str:
    if not s:
        return ""
    s = _HTML.sub(" ", str(s))
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()

def _norm_skills(skills: Iterable[str]) -> List[str]:
    out = []
    for x in skills or []:
        x = str(x).strip().lower()
        x = SKILL_SYNONYMS.get(x, x)
        if x:
            out.append(x)
    return sorted(set(out))

def _years_from_experiences(profile) -> Optional[float]:
    qs = profile.experiences.all()
    if not qs.exists():
        return None
    total_days = 0
    today = timezone.localdate()
    for e in qs:
        start = e.start_date
        end = e.end_date or today
        if start and end and end >= start:
            total_days += (end - start).days
    return round(total_days / 365.25, 2)

def _candidate_years(profile) -> float:
    y = _years_from_experiences(profile)
    if y is not None:
        return float(y)
    level_mid = {"entry": 1.0, "mid": 4.0, "senior": 8.0, "expert": 12.0}
    return float(level_mid.get(getattr(profile, "experience_level", ""), 2.0))

def _job_years_range(job) -> Tuple[float, float]:
    if job.__class__.__name__ == "JobPost":
        val = float(getattr(job, "experience_required", 0) or 0)
        unit = getattr(job, "experience_unit", "Years")
        years = val if unit == "Years" else val / 12.0
        return years, years + 1.0
    # Internship heuristic by level
    level = getattr(job, "level", None) or "Entry"
    return {"Entry": (0.0, 1.0), "Mid": (1.0, 3.0), "Senior": (3.0, 5.0)}.get(level, (0.0, 1.0))

def _location_fit(c_prov, c_city, j_prov, j_city, j_workplace) -> float:
    jw = (j_workplace or "").lower()
    if jw == "remote":
        return 0.8
    if c_city and j_city and str(c_city).lower() == str(j_city).lower():
        return 1.0
    if c_prov and j_prov and str(c_prov) == str(j_prov):
        return 0.7
    if jw == "hybrid":
        return 0.6
    return 0.3

def _experience_fit(c_years: float, jmin: float, jmax: float) -> float:
    if jmin <= c_years <= jmax:
        return 1.0
    gap = jmin - c_years if c_years < jmin else c_years - jmax
    return max(0.0, 1.0 - (gap / 5.0))  # lose 0.2 per year away

def _sector_match(cand_sectors: Iterable[str], job_sector: Optional[str]) -> float:
    if not job_sector:
        return 0.5
    js = str(job_sector).strip().lower()
    return 1.0 if js in [s.lower() for s in (cand_sectors or [])] else 0.6

def _cosine_binary(a: Iterable[str], b: Iterable[str]) -> float:
    A, B = set(a or []), set(b or [])
    if not A or not B:
        return 0.0
    inter = len(A & B)
    denom = sqrt(len(A) * len(B))
    return inter / denom if denom else 0.0

# ——————————————————————————————————————————
# Unify items (JobPost + InternshipPost) → JobLike
# ——————————————————————————————————————————
@dataclass
class JobLike:
    ct_id: int
    obj_id: int
    title: str
    sector: Optional[str]
    province: Optional[str]
    city: Optional[str]
    workplace: Optional[str]      # Onsite/Hybrid/Remote
    skills: List[str]
    exp_min: float
    exp_max: float
    created_at: timezone.datetime
    deadline: Optional[timezone.date]  # application deadline
    is_internship: bool = False

def _to_joblike(obj) -> JobLike:
    ct = ContentType.objects.get_for_model(obj).id
    if obj.__class__.__name__ == "JobPost":
        jmin, jmax = _job_years_range(obj)
        skills = [s.strip().lower() for s in obj.skills.names()] if hasattr(obj, "skills") else []
        return JobLike(
            ct_id=ct, obj_id=obj.id, title=obj.title,
            sector=getattr(obj, "sector", None),
            province=getattr(obj, "province", None),
            city=getattr(obj, "city", None),
            workplace=getattr(obj, "location_type", None),
            skills=_norm_skills(skills),
            exp_min=jmin, exp_max=jmax,
            created_at=getattr(obj, "created_at", timezone.now()),
            deadline=getattr(obj, "application_deadline", None),
            is_internship=False,
        )
    # InternshipPost
    jmin, jmax = _job_years_range(obj)
    skills = [s.strip().lower() for s in obj.skills.names()] if hasattr(obj, "skills") else []
    return JobLike(
        ct_id=ct, obj_id=obj.id, title=obj.title,
        sector=getattr(obj, "sector", None),
        province=getattr(obj, "province", None),     # if you don't store, leave None
        city=getattr(obj, "city", None),
        workplace=getattr(obj, "location", None),
        skills=_norm_skills(skills),
        exp_min=jmin, exp_max=jmax,
        created_at=getattr(obj, "created_at", timezone.now()),
        deadline=getattr(obj, "application_deadline", None),
        is_internship=True,
    )

def _iter_open_joblikes(filter_type: Optional[str] = None) -> List[JobLike]:
    """
    filter_type: None (all), 'jobs' (JobPost only), or 'internships' (InternshipPost only)
    """
    today = timezone.localdate()
    out: List[JobLike] = []
    
    classes_to_check = []
    if filter_type == "jobs":
        classes_to_check = [JobPost()]
    elif filter_type == "internships":
        classes_to_check = [InternshipPost()]
    else:
        classes_to_check = [JobPost(), InternshipPost()]

    for cls in classes_to_check:
        try:
            for o in cls.objects.filter(is_active=True):
                dl = getattr(o, "application_deadline", None)
                if dl and dl < today:
                    continue
                out.append(_to_joblike(o))
        except Exception:
            continue
    return out

# ——————————————————————————————————————————
# Content scoring (simple & fast)
# ——————————————————————————————————————————
@dataclass
class ContentResult:
    score: float
    why: str
    matched_skills: List[str]
    missing_skills: List[str]

def _build_match_reason(skills_sim: float, sector_s: float, loc_s: float, exp_s: float, title_sim: float, edu_sim: float = 0.0, is_internship: bool = False) -> str:
    reasons = []
    if skills_sim >= 0.5:
        reasons.append(f"Strong skill match ({int(skills_sim * 100)}%)")
    elif skills_sim > 0.0:
        reasons.append(f"Partial skill overlap ({int(skills_sim * 100)}%)")
    
    if is_internship and edu_sim >= 0.4:
        reasons.append("Matches education & field of study")

    if sector_s >= 0.9:
        reasons.append("Matches preferred sector")

    if loc_s >= 0.8:
        reasons.append("Location preference match")
    elif loc_s >= 0.6:
        reasons.append("Location fit")

    if exp_s >= 0.9:
        reasons.append("Experience level fit")

    if title_sim >= 0.4:
        reasons.append("Role title alignment")

    if not reasons:
        return "Recommended based on overall candidate profile alignment"
    return " • ".join(reasons)

def _content_score(profile, j: JobLike) -> ContentResult:
    # candidate features
    cand_sectors = [s.strip().lower() for s in (getattr(profile, "sectors_list", []) or []) if s.strip()]
    cand_skills = _norm_skills(getattr(profile, "skills_list", []) or [])
    c_years = _candidate_years(profile)

    # matched / missing skills
    j_skills_set = set(j.skills)
    c_skills_set = set(cand_skills)
    matched_skills = sorted(list(c_skills_set & j_skills_set))
    missing_skills = sorted(list(j_skills_set - c_skills_set))

    # content sub-scores
    skills_sim = _cosine_binary(cand_skills, j.skills)
    sector_s = _sector_match(cand_sectors, j.sector)
    exp_s = _experience_fit(c_years, j.exp_min, j.exp_max)
    loc_s = _location_fit(getattr(profile, "province", None), getattr(profile, "city", None),
                          j.province, j.city, j.workplace)

    # Education / Title alignment for Internships
    edu_sim = 0.0
    if j.is_internship:
        edu_fields = []
        if hasattr(profile, "educations"):
            edu_fields = [e.field_of_study.lower() for e in profile.educations.all() if e.field_of_study]
        title_tokens = set(re.findall(r"[a-zA-Z]{3,}", (j.title or "").lower()))
        designation_tokens = set(re.findall(r"[a-zA-Z]{3,}", (profile.designation or "").lower()))
        for ef in edu_fields:
            designation_tokens.update(re.findall(r"[a-zA-Z]{3,}", ef))
        edu_sim = _cosine_binary(designation_tokens, title_tokens)

        # Internship scoring formula (prioritizes education, skills, location fit)
        score = (
            0.45 * skills_sim +
            0.20 * edu_sim +
            0.15 * sector_s +
            0.10 * loc_s +
            0.10 * exp_s
        )
    else:
        p_title_tokens = {w for w in re.findall(r"[a-zA-Z]{3,}", (profile.designation or "").lower())}
        j_title_tokens = {w for w in re.findall(r"[a-zA-Z]{3,}", (j.title or "").lower())}
        title_sim = _cosine_binary(p_title_tokens, j_title_tokens)

        # Standard Job scoring formula
        score = (
            0.50 * skills_sim +
            0.15 * sector_s +
            0.15 * loc_s +
            0.10 * exp_s +
            0.10 * title_sim
        )

    why = _build_match_reason(skills_sim, sector_s, loc_s, exp_s, title_sim=edu_sim if j.is_internship else title_sim, edu_sim=edu_sim, is_internship=j.is_internship)
    return ContentResult(
        score=float(round(score, 6)),
        why=why,
        matched_skills=matched_skills,
        missing_skills=missing_skills
    )

# ——————————————————————————————————————————
# Collaborative (cosine on user–item matrix) — on the fly
# If you don’t have events, this returns 0 and hybrid becomes content-only.
# ——————————————————————————————————————————
ItemKey = Tuple[int, int]  # (ct_id, obj_id)

def _fetch_events_all_users() -> List[Tuple[int, ItemKey, float]]:
    Model = _candidate_event_model()
    if not Model:
        return []
    since = timezone.now() - timezone.timedelta(days=WINDOW_DAYS)
    rows = (Model.objects
            .filter(created_at__gte=since)
            .values_list("user_id", "item_content_type_id", "item_object_id", "event_type", "created_at"))
    out = []
    now = timezone.now()
    for uid, ct_id, obj_id, et, ts in rows:
        w = EVENT_WEIGHTS.get(et, 0.0)
        if w == 0.0:
            continue
        days = max(0, (now - ts).days)
        out.append((uid, (ct_id, obj_id), w * exp(-DECAY_LAMBDA * days)))
    return out

def _user_items_weighted(events: List[Tuple[int, ItemKey, float]]) -> Dict[int, List[Tuple[ItemKey, float]]]:
    by_user = defaultdict(list)
    for uid, item, w in events:
        by_user[uid].append((item, w))
    return by_user

def _cosine_item_sims_for_sources(events: List[Tuple[int, ItemKey, float]], sources: List[ItemKey]) -> Dict[ItemKey, float]:
    """
    Compute item-item cosine similarities ONLY for pairs that co-occur with the given source items.
    Returns a map: dst_item -> sim (max over sources or sum; we sum similarities).
    """
    if not events or not sources:
        return {}
    src_set = set(sources)
    by_user = _user_items_weighted(events)

    # accumulate dot products only for pairs touching a source item
    dot = defaultdict(float)
    norm2 = defaultdict(float)

    for uid, lst in by_user.items():
        # precompute norms contribution
        for (i, wi) in lst:
            norm2[i] += wi * wi
        # pairs
        n = len(lst)
        for a_idx in range(n):
            ia, wa = lst[a_idx]
            touch_a = ia in src_set
            for b_idx in range(a_idx + 1, n):
                ib, wb = lst[b_idx]
                if not (touch_a or ib in src_set):
                    continue  # only care if at least one is a source item
                dot[(ia, ib)] += wa * wb
                dot[(ib, ia)] += wa * wb

    # convert to similarities (only destinations where src in sources)
    sims = defaultdict(float)
    for (i, j), v in dot.items():
        if i not in src_set:
            continue
        n_i = sqrt(norm2[i]) if norm2[i] > 0 else 0.0
        n_j = sqrt(norm2[j]) if norm2[j] > 0 else 0.0
        if n_i == 0.0 or n_j == 0.0:
            continue
        sim = v / (n_i * n_j)
        sims[j] += sim
    return sims

def _user_source_items(user_id: int, events: List[Tuple[int, ItemKey, float]]) -> List[ItemKey]:
    return [item for (uid, item, w) in events if uid == user_id and w > 0]

# ——————————————————————————————————————————
# Public: call these from your views
# ——————————————————————————————————————————
@dataclass
class Ranked:
    ct_id: int
    obj_id: int
    score: float
    why: str
    matched_skills: List[str] = None
    missing_skills: List[str] = None
    is_internship: bool = False

def _recommend_for_candidate(user, filter_type: Optional[str] = None, limit: int = 20) -> List[Ranked]:
    # 0) fetch candidate profile
    try:
        profile = Profile().objects.select_related("user").prefetch_related("experiences", "educations").get(user=user)
    except Profile().DoesNotExist:
        return []

    # 1) gather open items
    items = _iter_open_joblikes(filter_type=filter_type)
    if not items:
        return []

    # 2) content scores
    content_map: Dict[ItemKey, ContentResult] = {}
    for j in items:
        c = _content_score(profile, j)
        content_map[(j.ct_id, j.obj_id)] = c

    # 3) collaborative scores (optional, from events)
    events = _fetch_events_all_users()
    cf_scores: Dict[ItemKey, float] = {}
    alpha = 0.3  # weight of CF in hybrid
    if events:
        src = _user_source_items(user.id, events)
        if src:
            sims = _cosine_item_sims_for_sources(events, src)
            cf_scores = sims

    # 4) hybrid + rank
    item_by_key = {(j.ct_id, j.obj_id): j for j in items}
    ranked = []
    for key, cres in content_map.items():
        cf = cf_scores.get(key, 0.0)
        score = (1 - alpha) * cres.score + alpha * cf
        why_str = cres.why + (f" • Collaborative activity boost" if cf > 0 else "")
        j_item = item_by_key[key]
        ranked.append((
            key,
            score,
            why_str,
            cres.matched_skills,
            cres.missing_skills,
            j_item.is_internship
        ))

    ranked.sort(key=lambda x: x[1], reverse=True)
    ranked = ranked[:limit]

    # 5) wrap
    return [
        Ranked(
            ct_id=k[0],
            obj_id=k[1],
            score=float(round(s, 6)),
            why=why,
            matched_skills=m_skills or [],
            missing_skills=miss_skills or [],
            is_internship=is_intern
        )
        for (k, s, why, m_skills, miss_skills, is_intern) in ranked
    ]

def recommend_jobs_for_candidate(user, limit: int = 20) -> List[Ranked]:
    return _recommend_for_candidate(user, filter_type="jobs", limit=limit)

def recommend_internships_for_candidate(user, limit: int = 20) -> List[Ranked]:
    return _recommend_for_candidate(user, filter_type="internships", limit=limit)

def recommend_all_for_candidate(user, limit: int = 20) -> List[Ranked]:
    return _recommend_for_candidate(user, filter_type=None, limit=limit)

def recommend_candidates_for_job(job_obj, limit: int = 50) -> List[Ranked]:
    # 0) item unify
    j = _to_joblike(job_obj)

    # 1) candidate pool
    profs = Profile().objects.all().prefetch_related("experiences", "projects", "educations")
    if not profs.exists():
        return []

    # 2) content score per candidate
    tmp = []
    for p in profs:
        c = _content_score(p, j)
        tmp.append((p.id, c.score, c.why, c.matched_skills, c.missing_skills))

    # 3) collaborative lift: users who interacted with items similar to this job
    events = _fetch_events_all_users()
    cf_map_user: Dict[int, float] = defaultdict(float)
    if events:
        ct = ContentType.objects.get_for_model(job_obj).id
        src = [(ct, job_obj.id)]
        sims = _cosine_item_sims_for_sources(events, src)

        by_user = _user_items_weighted(events)
        for uid, lst in by_user.items():
            s = 0.0
            for (item, w) in lst:
                sim = sims.get(item, 0.0)
                if sim > 0 and w > 0:
                    s += sim * w
            if s > 0:
                cf_map_user[uid] = min(1.0, s)

    alpha = 0.25
    ranked = []
    prof_ct = ContentType.objects.get_for_model(Profile())
    id_to_user = dict(profs.values_list("id", "user_id"))

    for pid, cscore, why, m_skills, miss_skills in tmp:
        uid = id_to_user.get(pid)
        cf = cf_map_user.get(uid, 0.0)
        score = (1 - alpha) * cscore + alpha * cf
        why_str = why + (f" • Collaborative activity boost" if cf > 0 else "")
        ranked.append(((prof_ct.id, pid), score, why_str, m_skills, miss_skills, False))

    ranked.sort(key=lambda x: x[1], reverse=True)
    ranked = ranked[:limit]
    return [
        Ranked(
            ct_id=k[0],
            obj_id=k[1],
            score=float(round(s, 6)),
            why=why,
            matched_skills=m_skills or [],
            missing_skills=miss_skills or [],
            is_internship=is_intern
        )
        for (k, s, why, m_skills, miss_skills, is_intern) in ranked
    ]

