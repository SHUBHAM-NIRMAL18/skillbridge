import os
import mimetypes
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponse, FileResponse, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from datetime import timedelta
from candidate.models import Profile
from company.models import CompanyProfile, JobPost, InternshipPost
from .models import Application, OfferLetter
from .forms import OfferLetterForm
from django.db.models import Count, Q
from django.core.paginator import Paginator



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
    kind = request.GET.get("type")
    pk   = request.GET.get("id")
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER", "/")
    if not kind or not pk:
        return HttpResponseBadRequest("Missing parameters.")

    post, company = _get_target(kind, pk)
    if post is None:
        return HttpResponseBadRequest("Invalid target.")

    # prevent companies from applying
    if hasattr(request.user, "company_profile"):
        return render(request, "applications/_apply_modal.html", {
            "company_cannot_apply": True, 
            "post": post, 
            "kind": kind, 
            "next_url": next_url,
        })

    # candidate profile
    try:
        profile = Profile.objects.select_related("user").get(user=request.user)
    except Profile.DoesNotExist:
        return render(request, "applications/_apply_modal.html", {
            "need_profile": True, "next_url": next_url, "kind": kind, "post": post,
        })

    # ADD THIS CHECK - validate profile completeness
    if not profile.resume:
        return render(request, "applications/_apply_modal.html", {
            "incomplete_profile": True, 
            "missing": "resume",
            "post": post, 
            "kind": kind, 
            "next_url": next_url,
        })

    # closed?
    if not _deadline_open(post):
        return render(request, "applications/_apply_modal.html", {
            "closed": True, "post": post, "kind": kind, "next_url": next_url,
        })

    # ✅ allow re-apply: ONLY block if existing is NOT withdrawn/rejected
    existing = Application.objects.filter(
        candidate=profile,
        job_post=post if kind == "job" else None,
        internship_post=post if kind == "intern" else None,
    ).first()
    already = bool(existing and existing.status not in ("withdrawn", "rejected"))

    return render(request, "applications/_apply_modal.html", {
        "profile": profile,
        "post": post,
        "company": company,
        "kind": kind,
        "next_url": next_url,
        "already": already,                 # False for withdrawn/rejected → show form
        "existing_status": existing.status if existing else None,
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

    # Log application event for recommendation engine & clear recommendations cache
    try:
        from django.contrib.contenttypes.models import ContentType
        from recommendations.models import CandidateEvent
        from recommendations.simple_hybrid import invalidate_candidate_rec_cache
        target_obj = post
        ct = ContentType.objects.get_for_model(target_obj)
        CandidateEvent.objects.create(
            user=request.user,
            item_content_type=ct,
            item_object_id=target_obj.id,
            event_type="apply"
        )
        invalidate_candidate_rec_cache(request.user.id)
    except Exception:
        pass

    # Fire notification to company
    try:
        from communications.services import notify_user
        notify_user(
            recipient=company.user,
            title="New Application Received",
            message=f"{profile.first_name} {profile.last_name} submitted an application for {post.title}.",
            action_url=reverse("company:applicants_all"),
            sender=request.user,
            notification_type="new_application"
        )
    except Exception:
        pass

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


# Map UI tab keys -> internal statuses
TAB_MAP = {
    "all": None,
    "pending": "applied",
    "viewed": "under_review",      # label "Viewed" in UI
    "shortlisted": "shortlisted",
    "offered": "offered",
    "rejected": "rejected",
    "withdrawn": "withdrawn",
}

@login_required(login_url="accounts:login")
def my_applications(request):
    profile = Profile.objects.filter(user=request.user).first()
    if not profile:
        messages.info(request, "Create your candidate profile to see your applications.")
        return redirect("/candidate/")

    base = (Application.objects
            .select_related("company", "job_post", "internship_post")
            .filter(candidate=profile))

    # counts for tabs
    counts = dict(base.values("status").annotate(c=Count("id")).values_list("status", "c"))
    total_all = base.count()
    total_job = base.filter(job_post__isnull=False).count()
    total_int = base.filter(internship_post__isnull=False).count()

    # filters from querystring
    tab   = request.GET.get("tab", "all")           # all | pending | viewed | shortlisted | offered | rejected | withdrawn
    typ   = request.GET.get("type", "all")          # all | job | intern
    q     = request.GET.get("q", "").strip()
    sort  = request.GET.get("sort", "newest")       # newest | oldest

    qs = base
    if typ == "job":
        qs = qs.filter(job_post__isnull=False)
    elif typ == "intern":
        qs = qs.filter(internship_post__isnull=False)

    status = TAB_MAP.get(tab)
    if status:
        qs = qs.filter(status=status)

    if q:
        qs = qs.filter(
            Q(job_post__title__icontains=q) |
            Q(internship_post__title__icontains=q) |
            Q(company__first_name__icontains=q) |
            Q(company__last_name__icontains=q)
        )

    qs = qs.order_by("-applied_at" if sort == "newest" else "applied_at")

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    ctx = {
        "tab": tab, "typ": typ, "q": q, "sort": sort,
        "page_obj": page_obj, "apps": page_obj.object_list,
        "counts": counts, "total_all": total_all, "total_job": total_job, "total_int": total_int,
    }
    return render(request, "applications/candidate_table.html", ctx)


@login_required(login_url="accounts:login")
@require_POST
def delete_application(request, pk: int):
    app = get_object_or_404(Application.objects.select_related("candidate__user"), pk=pk)
    # owner only
    if app.candidate.user_id != request.user.id:
        return HttpResponseForbidden("Not allowed.")
    
    app.delete()
    messages.success(request, f"Application for '{app.target_title}' deleted permanently.")
    return redirect("applications:my_applications")


@login_required(login_url="accounts:login")
def application_detail(request, pk: int):
    app = get_object_or_404(
        Application.objects.select_related("candidate__user", "company", "job_post", "internship_post"), 
        pk=pk
    )
    # owner only
    if app.candidate.user_id != request.user.id:
        return HttpResponseForbidden("Not allowed.")
    
    return render(request, "applications/_application_detail.html", {"app": app})


# ==========================================
# OFFER LETTER WORKFLOW VIEWS
# ==========================================

@login_required(login_url="accounts:login")
def create_offer_letter(request, app_id: int):
    """
    Company-side view to create or edit an Offer Letter for a candidate application.
    """
    if not hasattr(request.user, "company_profile"):
        return HttpResponseForbidden("Company profile required.")

    company = request.user.company_profile
    app = get_object_or_404(
        Application.objects.select_related("candidate__user", "company", "job_post", "internship_post"),
        pk=app_id,
        company=company
    )

    offer, created = OfferLetter.objects.get_or_create(
        application=app,
        defaults={
            "company": company,
            "candidate": app.candidate,
            "job_title": app.target_title,
            "offered_salary": "NPR 35,000 / month",
            "joining_date": timezone.localdate() + timedelta(days=14),
            "expiration_date": timezone.localdate() + timedelta(days=7),
            "work_location": getattr(app.job_post or app.internship_post, "city", "Kathmandu"),
            "employment_type": "Full Time Job" if app.is_job else "Internship",
            "hr_name": f"{company.first_name} {company.last_name}",
            "hr_designation": "Hiring Manager",
            "terms_and_conditions": (
                "CLAUSE 1: APPOINTMENT, POSITION & REPORTING HIERARCHY\n"
                "You are formally appointed to the position specified in this offer letter. In this role, you will be expected to carry out all core duties associated with your position and report directly to your assigned Department Head or Hiring Manager. The company reserves the right to align your job title or reporting line in accordance with organizational evolution.\n\n"
                "CLAUSE 2: SCOPE OF DUTIES & PERFORMANCE EXPECTATIONS\n"
                "Your responsibilities encompass high-quality execution of assigned technical, operational, and project tasks. You are required to perform your duties with diligence, maintain high professional standards, meet project milestones, collaborate effectively with team members, and comply with all reasonable directives issued by company leadership.\n\n"
                "CLAUSE 3: COMPENSATION, PAYROLL SCHEDULE & TAX DEDUCTIONS\n"
                "Your total monthly compensation will be disbursed on or before the last working day of each calendar month via direct transfer to your registered bank account. All payments are subject to mandatory government Tax Deducted at Source (TDS), statutory withholdings, and deductions in compliance with prevailing tax regulations and labor laws.\n\n"
                "CLAUSE 4: PERFORMANCE BONUSES, ALLOWANCES & REIMBURSEMENTS\n"
                "In addition to your base remuneration, you may be eligible for discretionary performance-based bonuses, project incentives, or statutory allowances evaluated during annual performance reviews. Legitimate business-related expenses incurred during authorized official duties will be reimbursed upon submitting valid receipts.\n\n"
                "CLAUSE 5: PROBATIONARY PERIOD & CONFIRMATION EVALUATION\n"
                "Your appointment commences with a mandatory 3-month probationary period. During probation, your work performance, technical competency, punctuality, and cultural alignment will be regularly reviewed. Upon satisfactory evaluation, your employment will be confirmed in writing. If performance does not meet required standards, probation may be extended or terminated.\n\n"
                "CLAUSE 6: WORKING HOURS, OVERTIME & BREAK SCHEDULE\n"
                "Standard working hours are 40 hours per week, Monday through Friday, from 9:00 AM to 5:00 PM, with a 1-hour lunch and refreshment break. You may occasionally be required to adjust working hours or extend time to fulfill critical project deadlines or client requirements in accordance with company policy.\n\n"
                "CLAUSE 7: LEAVE ENTITLEMENT, SICK LEAVES & PUBLIC HOLIDAYS\n"
                "You are entitled to annual paid leaves, paid sick leave, and casual leave accrued per completed month of service following probation. You are also entitled to official public holidays observed in the company calendar. Prior written approval from your manager is required for all scheduled leave requests.\n\n"
                "CLAUSE 8: WORK LOCATION, HYBRID & REMOTE WORK GUIDELINES\n"
                "Your primary workplace location is specified in this offer. If operating under an approved hybrid or remote arrangement, you must maintain a secure, reliable internet connection, adhere to data security protocols, and remain available during core office hours. The company reserves the right to recall remote employees to office upon prior notice.\n\n"
                "CLAUSE 9: CONFIDENTIALITY, DATA SECURITY & NON-DISCLOSURE (NDA)\n"
                "You shall maintain absolute confidentiality regarding all company intellectual property, proprietary software source code, customer records, financial accounts, trade secrets, and business operational strategies. You shall not disclose, copy, or transmit any confidential information to unauthorized third parties during or after your employment.\n\n"
                "CLAUSE 10: INTELLECTUAL PROPERTY RIGHTS & WORK PRODUCT ASSIGNMENT\n"
                "All software applications, code, designs, algorithms, technical documentation, business workflows, and inventions developed, conceived, or authored by you during your employment shall be the sole and exclusive intellectual property of the company from creation. You hereby assign all worldwide IP rights to the company.\n\n"
                "CLAUSE 11: CODE OF CONDUCT, ETHICS & WORKPLACE DIGNITY\n"
                "You agree to uphold strict ethical standards, professionalism, respect, and integrity in all interactions. The company maintains zero tolerance for workplace harassment, discrimination, substance abuse, or unauthorized external commercial activities that conflict with your primary employment responsibilities.\n\n"
                "CLAUSE 12: NON-SOLICITATION & EXCLUSIVITY OF SERVICE\n"
                "During your employment, you agree not to engage in secondary employment, consulting, or commercial activities without prior written authorization. For a period of 12 months post-employment, you agree not to solicit or recruit company clients, business partners, or employees for competing ventures.\n\n"
                "CLAUSE 13: TERMINATION PROCEDURE & NOTICE PERIOD\n"
                "During the probation period, either party may terminate employment by providing 15 days prior written notice. Post-confirmation, a 30-day written notice or equivalent basic salary in lieu of notice is required. The company reserves the right to terminate employment immediately without notice in cases of gross misconduct, fraud, breach of confidentiality, or criminal conviction.\n\n"
                "CLAUSE 14: GOVERNING LAW, DISPUTE RESOLUTION & DIGITAL ACCEPTANCE\n"
                "This offer of employment is governed by and construed under the labor laws of Nepal. Any disputes arising hereunder shall be resolved through mutual consultation or appropriate legal jurisdiction. Please confirm your acceptance digitally via your SkillBridge portal prior to the offer expiration date."
            )
        }
    )

    if request.method == "POST":
        form = OfferLetterForm(request.POST, request.FILES, instance=offer)
        if form.is_valid():
            offer_obj = form.save(commit=False)
            offer_obj.status = "pending"
            offer_obj.save()

            # Update Application status to offered
            app.status = "offered"
            app.save(update_fields=["status", "updated_at"])

            # Fire notification to candidate
            try:
                from communications.services import notify_user
                notify_user(
                    recipient=app.candidate.user,
                    title="Formal Offer Letter Issued!",
                    message=f"{app.company.company_name} has issued an employment offer letter for {app.target_title}.",
                    action_url=reverse("applications:view_offer", args=[app.id]),
                    sender=request.user,
                    notification_type="offer_letter"
                )
            except Exception:
                pass

            messages.success(request, f"Offer Letter successfully issued to {app.candidate.first_name}!")
            return redirect("company:applicants_all")
    else:
        form = OfferLetterForm(instance=offer)

    return render(request, "applications/offer_form.html", {
        "form": form,
        "app": app,
        "offer": offer,
    })


@login_required(login_url="accounts:login")
def view_offer_letter(request, app_id: int):
    """
    View offer letter detail (accessible by Candidate or issuing Company).
    """
    app = get_object_or_404(
        Application.objects.select_related("candidate__user", "company", "job_post", "internship_post"),
        pk=app_id
    )

    # Authorization: user must be candidate or company owner
    is_candidate = hasattr(request.user, "profile") and app.candidate.user_id == request.user.id
    is_company = hasattr(request.user, "company_profile") and app.company.user_id == request.user.id

    if not (is_candidate or is_company):
        return HttpResponseForbidden("Access denied.")

    try:
        offer = app.offer_letter
    except OfferLetter.DoesNotExist:
        messages.error(request, "No offer letter has been issued for this application yet.")
        if is_company:
            return redirect("company:applicants_all")
        return redirect("applications:my_applications")

    # Auto-expire check
    if offer.is_expired:
        offer.status = "expired"
        offer.save(update_fields=["status", "updated_at"])

    # Auto-upgrade terms if empty or missing comprehensive clauses
    if not offer.terms_and_conditions or "CLAUSE 1:" not in offer.terms_and_conditions:
        offer.terms_and_conditions = (
            "CLAUSE 1: APPOINTMENT, POSITION & REPORTING HIERARCHY\n"
            "You are formally appointed to the position specified in this offer letter. In this role, you will be expected to carry out all core duties associated with your position and report directly to your assigned Department Head or Hiring Manager. The company reserves the right to align your job title or reporting line in accordance with organizational evolution.\n\n"
            "CLAUSE 2: SCOPE OF DUTIES & PERFORMANCE EXPECTATIONS\n"
            "Your responsibilities encompass high-quality execution of assigned technical, operational, and project tasks. You are required to perform your duties with diligence, maintain high professional standards, meet project milestones, collaborate effectively with team members, and comply with all reasonable directives issued by company leadership.\n\n"
            "CLAUSE 3: COMPENSATION, PAYROLL SCHEDULE & TAX DEDUCTIONS\n"
            "Your total monthly compensation will be disbursed on or before the last working day of each calendar month via direct transfer to your registered bank account. All payments are subject to mandatory government Tax Deducted at Source (TDS), statutory withholdings, and deductions in compliance with prevailing tax regulations and labor laws.\n\n"
            "CLAUSE 4: PERFORMANCE BONUSES, ALLOWANCES & REIMBURSEMENTS\n"
            "In addition to your base remuneration, you may be eligible for discretionary performance-based bonuses, project incentives, or statutory allowances evaluated during annual performance reviews. Legitimate business-related expenses incurred during authorized official duties will be reimbursed upon submitting valid receipts.\n\n"
            "CLAUSE 5: PROBATIONARY PERIOD & CONFIRMATION EVALUATION\n"
            "Your appointment commences with a mandatory 3-month probationary period. During probation, your work performance, technical competency, punctuality, and cultural alignment will be regularly reviewed. Upon satisfactory evaluation, your employment will be confirmed in writing. If performance does not meet required standards, probation may be extended or terminated.\n\n"
            "CLAUSE 6: WORKING HOURS, OVERTIME & BREAK SCHEDULE\n"
            "Standard working hours are 40 hours per week, Monday through Friday, from 9:00 AM to 5:00 PM, with a 1-hour lunch and refreshment break. You may occasionally be required to adjust working hours or extend time to fulfill critical project deadlines or client requirements in accordance with company policy.\n\n"
            "CLAUSE 7: LEAVE ENTITLEMENT, SICK LEAVES & PUBLIC HOLIDAYS\n"
            "You are entitled to annual paid leaves, paid sick leave, and casual leave accrued per completed month of service following probation. You are also entitled to official public holidays observed in the company calendar. Prior written approval from your manager is required for all scheduled leave requests.\n\n"
            "CLAUSE 8: WORK LOCATION, HYBRID & REMOTE WORK GUIDELINES\n"
            "Your primary workplace location is specified in this offer. If operating under an approved hybrid or remote arrangement, you must maintain a secure, reliable internet connection, adhere to data security protocols, and remain available during core office hours. The company reserves the right to recall remote employees to office upon prior notice.\n\n"
            "CLAUSE 9: CONFIDENTIALITY, DATA SECURITY & NON-DISCLOSURE (NDA)\n"
            "You shall maintain absolute confidentiality regarding all company intellectual property, proprietary software source code, customer records, financial accounts, trade secrets, and business operational strategies. You shall not disclose, copy, or transmit any confidential information to unauthorized third parties during or after your employment.\n\n"
            "CLAUSE 10: INTELLECTUAL PROPERTY RIGHTS & WORK PRODUCT ASSIGNMENT\n"
            "All software applications, code, designs, algorithms, technical documentation, business workflows, and inventions developed, conceived, or authored by you during your employment shall remain the sole and exclusive intellectual property of the company from creation. You hereby assign all worldwide IP rights to the company.\n\n"
            "CLAUSE 11: CODE OF CONDUCT, ETHICS & WORKPLACE DIGNITY\n"
            "You agree to uphold strict ethical standards, professionalism, respect, and integrity in all interactions. The company maintains zero tolerance for workplace harassment, discrimination, substance abuse, or unauthorized external commercial activities that conflict with your primary employment responsibilities.\n\n"
            "CLAUSE 12: NON-SOLICITATION & EXCLUSIVITY OF SERVICE\n"
            "During your employment, you agree not to engage in secondary employment, consulting, or commercial activities without prior written authorization. For a period of 12 months post-employment, you agree not to solicit or recruit company clients, business partners, or employees for competing ventures.\n\n"
            "CLAUSE 13: TERMINATION PROCEDURE & NOTICE PERIOD\n"
            "During the probation period, either party may terminate employment by providing 15 days prior written notice. Post-confirmation, a 30-day written notice or equivalent basic salary in lieu of notice is required. The company reserves the right to terminate employment immediately without notice in cases of gross misconduct, fraud, breach of confidentiality, or criminal conviction.\n\n"
            "CLAUSE 14: GOVERNING LAW, DISPUTE RESOLUTION & DIGITAL ACCEPTANCE\n"
            "This offer of employment is governed by and construed under the labor laws of Nepal. Any disputes arising hereunder shall be resolved through mutual consultation or appropriate legal jurisdiction. Please confirm your acceptance digitally via your SkillBridge portal prior to the offer expiration date."
        )
        offer.save(update_fields=["terms_and_conditions", "updated_at"])

    return render(request, "applications/offer_detail.html", {
        "app": app,
        "offer": offer,
        "is_candidate": is_candidate,
        "is_company": is_company,
    })


@login_required(login_url="accounts:login")
@require_POST
def respond_offer_letter(request, app_id: int):
    """
    Candidate response (Accept / Decline) to an offer letter.
    """
    app = get_object_or_404(Application.objects.select_related("candidate__user"), pk=app_id)

    if app.candidate.user_id != request.user.id:
        return HttpResponseForbidden("Access denied.")

    offer = get_object_or_404(OfferLetter, application=app)

    if offer.status != "pending" or offer.is_expired:
        messages.error(request, "This offer is no longer pending or has expired.")
        return redirect("applications:view_offer", app_id=app.id)

    action = request.POST.get("action")
    notes = request.POST.get("notes", "").strip()

    if action == "accept":
        offer.status = "accepted"
        offer.accepted_at = timezone.now()
        offer.candidate_response_notes = notes
        offer.save()

        app.status = "accepted"
        app.save(update_fields=["status", "updated_at"])

        messages.success(request, "🎉 Congratulations! You have accepted the Offer Letter. The employer has been notified.")
    elif action == "decline":
        offer.status = "declined"
        offer.candidate_response_notes = notes
        offer.save()

        app.status = "rejected"
        app.save(update_fields=["status", "updated_at"])

        messages.info(request, "You have declined the offer letter.")

    # Fire notification to company
    try:
        from communications.services import notify_user
        status_verb = "accepted" if action == "accept" else "declined"
        notify_user(
            recipient=app.company.user,
            title=f"Offer Letter {status_verb.capitalize()}!",
            message=f"{app.candidate.first_name} {app.candidate.last_name} has {status_verb} the offer letter for {app.target_title}.",
            action_url=reverse("applications:view_offer", args=[app.id]),
            sender=request.user,
            notification_type="offer_letter"
        )
    except Exception:
        pass

    return redirect("applications:view_offer", app_id=app.id)


@login_required(login_url="accounts:login")
def download_application_resume(request, pk: int):
    """
    Protected resume streaming view for an application.
    Ensures only the candidate owner, the hiring company, or admin can access.
    """
    app = get_object_or_404(
        Application.objects.select_related("candidate__user", "company__user"),
        pk=pk
    )

    if not app.resume_file:
        raise Http404("No resume attached to this application.")

    is_owner = (app.candidate.user_id == request.user.id)
    is_company = (app.company.user_id == request.user.id)
    is_staff = request.user.is_staff

    if not (is_owner or is_company or is_staff):
        return HttpResponseForbidden("You do not have authorization to view this application resume.")

    file_path = app.resume_file.path
    if not os.path.exists(file_path):
        raise Http404("Resume file was not found on the server.")

    content_type, _ = mimetypes.guess_type(file_path)
    content_type = content_type or "application/pdf"

    response = FileResponse(open(file_path, "rb"), content_type=content_type)
    filename = os.path.basename(app.resume_file.name)
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response