from django.shortcuts import render

# Create your views here.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from candidate.models import Profile
from company.models import CompanyProfile, JobPost, InternshipPost
from .models import Application

def _get_target(kind: str, pk: int):
    if kind == "job":
        post = get_object_or_404(JobPost.objects.select_related("company"), pk=pk)
    elif kind == "intern":
        post = get_object_or_404(InternshipPost.objects.select_related("company"), pk=pk)
    else:
        return None, None
    return post, post.company

def _deadline_open(post):
    today = timezone.localdate()
    return bool(post.is_active and post.application_deadline >= today)

@require_GET
@login_required(login_url="accounts:login")
def apply_preview(request):
    """
    Return the modal HTML with candidate summary for the given post.
    GET params: ?type=job|intern&id=<pk>&next=<url>
    """
    kind = request.GET.get("type")
    pk   = request.GET.get("id")
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER", "/")

    if not kind or not pk:
        return HttpResponseBadRequest("Missing parameters.")

    post, company = _get_target(kind, pk)
    if post is None:
        return HttpResponseBadRequest("Invalid target.")

    # candidate profile
    try:
        profile = Profile.objects.select_related("user").get(user=request.user)
    except Profile.DoesNotExist:
        # Render a minimal modal prompting to create profile
        return render(request, "applications/_apply_modal.html", {
            "need_profile": True,
            "next_url": next_url,
            "kind": kind,
            "post": post,
        })

    # guards
    if not _deadline_open(post):
        return render(request, "applications/_apply_modal.html", {
            "closed": True, "post": post, "kind": kind, "next_url": next_url,
        })

    # already applied?
    already = Application.objects.filter(
        candidate=profile,
        job_post=post if kind == "job" else None,
        internship_post=post if kind == "intern" else None,
    ).exists()

    return render(request, "applications/_apply_modal.html", {
        "profile": profile,
        "post": post,
        "company": company,
        "kind": kind,
        "next_url": next_url,
        "already": already,
    })

@require_POST
@login_required(login_url="accounts:login")
def apply_submit(request):
    kind     = request.POST.get("kind")
    post_id  = request.POST.get("post_id")
    next_url = request.POST.get("next") or "/"
    cover    = request.POST.get("cover_letter", "").strip()
    file_in  = request.FILES.get("resume")

    if not kind or not post_id:
        return JsonResponse({"ok": False, "error": "Missing parameters."}, status=400)

    post, company = _get_target(kind, post_id)
    if post is None:
        return JsonResponse({"ok": False, "error": "Invalid posting."}, status=400)

    # candidate profile & resume
    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        return JsonResponse({"ok": False, "redirect": "/candidate/", "error": "Create your candidate profile first."}, status=400)

    if not _deadline_open(post):
        return JsonResponse({"ok": False, "error": "Applications are closed."}, status=400)

    # prevent posting owner from applying
    if hasattr(request.user, "company_profile") and post.company_id == request.user.company_profile.id:
        return JsonResponse({"ok": False, "error": "You cannot apply to your own posting."}, status=403)

    # --- DEDUPE / RE-APPLY LOGIC ---
    # find existing application for this candidate & target
    existing = Application.objects.filter(
        candidate=profile,
        job_post=post if kind == "job" else None,
        internship_post=post if kind == "intern" else None,
    ).first()

    if existing:
        # allow re-apply if previously withdrawn or rejected: flip back to "applied"
        if existing.status in ("withdrawn", "rejected"):
            # choose resume: uploaded > profile.resume > existing.resume_file
            resume_to_use = file_in or profile.resume or existing.resume_file
            if not resume_to_use:
                return JsonResponse({"ok": False, "error": "Please upload your resume first in your profile."}, status=400)

            if file_in:
                existing.resume_file = file_in
            elif not existing.resume_file and profile.resume:
                existing.resume_file = profile.resume

            if cover:
                existing.cover_letter = cover

            existing.status = "applied"
            # refresh applied_at so it sorts as a new submission
            from django.utils import timezone
            existing.applied_at = timezone.now()
            existing.save(update_fields=["resume_file", "cover_letter", "status", "applied_at", "updated_at"])
            messages.success(request, "Application re-submitted successfully.")
            return JsonResponse({"ok": True, "redirect": next_url})
        # otherwise treat as idempotent (already applied / in pipeline)
        return JsonResponse({"ok": True, "redirect": next_url})

    # --- CREATE NEW APPLICATION ---
    app = Application(
        candidate=profile,
        company=company,
        cover_letter=cover or "",
        status="applied",
        job_post=post if kind == "job" else None,
        internship_post=post if kind == "intern" else None,
    )

    # attach resume: uploaded file wins; else use saved profile resume (if any)
    if file_in:
        app.resume_file = file_in
    elif profile.resume:
        app.resume_file = profile.resume
    else:
        return JsonResponse({"ok": False, "error": "Please upload your resume first in your profile."}, status=400)

    app.save()
    messages.success(request, "Application submitted successfully.")
    return JsonResponse({"ok": True, "redirect": next_url})


@login_required(login_url="accounts:login")
def my_applications(request):
    profile = Profile.objects.filter(user=request.user).first()
    if not profile:
        messages.info(request, "Create your candidate profile to see your applications.")
        return redirect("/candidate/")

    qs = (Application.objects
          .select_related("company", "job_post", "internship_post")
          .filter(candidate=profile))

    # simple filters
    t = request.GET.get("type")
    s = request.GET.get("status")
    if t == "job":
        qs = qs.filter(job_post__isnull=False)
    elif t == "intern":
        qs = qs.filter(internship_post__isnull=False)
    if s:
        qs = qs.filter(status=s)

    return render(request, "applications/candidate_list.html", {"apps": qs})

@login_required(login_url="accounts:login")
@require_POST
def withdraw_application(request, pk: int):
    app = get_object_or_404(Application.objects.select_related("candidate__user"), pk=pk)
    # owner only
    if app.candidate.user_id != request.user.id:
        return HttpResponseForbidden("Not allowed.")
    if app.status in {"applied", "under_review"}:
        app.status = "withdrawn"
        app.save(update_fields=["status", "updated_at"])
        messages.success(request, "Application withdrawn.")
    return redirect("applications:my_applications")
