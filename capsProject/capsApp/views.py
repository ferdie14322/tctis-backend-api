from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view
from .models import User, Ticket, Violation, Ticket, Dispute
from .serializers import (
    UserSerializer,
    LoginSerializer,
    TicketSerializer,
    TicketSerializer2,
    DisputeSerializer,
)
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from datetime import datetime
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth, TruncDay
from datetime import datetime, timedelta
from collections import OrderedDict
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Ticket, Violation
from django.core.paginator import Paginator
from django.db.models import Q


class UserProfileAPIView(APIView):
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            return Response(
                {
                    "user_id": user.id,
                    "firstname": user.firstname,
                    "lastname": user.lastname,
                    "username": user.username,
                    "mobile_number": user.mobile_number,
                    "role": user.role,
                },
                status=status.HTTP_200_OK,
            )
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class SignupAPIView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "User registered successfully"},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data["username"]
            password = serializer.validated_data["password"]
            requested_role = request.data.get("role")  

            try:
                user = User.objects.get(username=username)
                if user.check_password(password):
                    # Verify the user's actual role matches the requested role
                    if user.role.lower() != requested_role.lower():
                        return Response(
                            {"error": f"User is not a {requested_role}"},
                            status=status.HTTP_403_FORBIDDEN,
                        )
                    
                    return Response(
                        {
                            "message": "Login successful",
                            "user_id": user.id,
                            "firstname": user.firstname,
                            "lastname": user.lastname,
                            "role": user.role,  # Send back the actual role
                        },
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        {"error": "Password incorrect"},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
            except User.DoesNotExist:
                return Response(
                    {"error": "Account not found"}, status=status.HTTP_404_NOT_FOUND
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserDisputesAPIView(APIView):
    def get(self, request, user_id):
        try:
            disputes = Dispute.objects.filter(filed_by_id=user_id)
            serializer = DisputeSerializer(disputes, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


def search_tickets(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if start_date and end_date:

        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        print(f"Searching tickets from {start_date} to {end_date}")

        tickets = Ticket.objects.filter(
            created_at__range=[start_date, end_date]
        ).select_related("user_id", "violation_details", "issued_by")

        print(f"Tickets found: {tickets}")
    else:
        tickets = Ticket.objects.all().select_related(
            "user_id", "violation_details", "issued_by"
        )

    ticket_data = []
    for ticket in tickets:
        ticket_data.append(
            {
                "ticket_id": ticket.id,
                "license_no": ticket.license_no,
                "plate_number": ticket.plate_number,
                "user": {
                    "username": ticket.user_id.username,
                    "firstname": ticket.user_id.firstname,
                    "lastname": ticket.user_id.lastname,
                    "role": ticket.user_id.role,
                },
                "violation": {
                    "name": ticket.violation_details.name,
                    "penalty_amount": str(ticket.violation_details.penalty_amount),
                },
                "fine_amount": ticket.fine_amount,
                "issued_by": {
                    "username": ticket.issued_by.username,
                    "firstname": ticket.issued_by.firstname,
                    "lastname": ticket.issued_by.lastname,
                    "role": ticket.issued_by.role,
                },
                "status": ticket.status,
                "created_at": ticket.created_at,
                "due_date": ticket.due_date,
            }
        )

    return JsonResponse(ticket_data, safe=False)


@api_view(["POST"])
def submit_dispute(request):
    try:

        ticket_id = request.data.get("ticket")
        if not Ticket.objects.filter(id=ticket_id).exists():
            return Response(
                {"error": f"Ticket with ID {ticket_id} does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = DisputeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Dispute submitted successfully"},
                status=status.HTTP_201_CREATED,
            )
        else:
            print("Validation errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(f"Error in submit_dispute: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def get_ticketsByPoliceCounts(request, user_id=None):
    if not user_id:
        return Response({"error": "User ID required"}, status=400)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    total_tickets = Ticket.objects.filter(issued_by=user).count()
    pending_tickets = Ticket.objects.filter(issued_by=user, status="Pending").count()
    resolved_disputes = Ticket.objects.filter(issued_by=user, status="Resolved").count()

    counts = {
        "total_tickets": total_tickets,
        "pending_tickets": pending_tickets,
        "resolved_disputes": resolved_disputes,
    }

    return Response(counts)


@api_view(["GET"])
def get_recent_activity(request, user_id):
    recent_tickets = Ticket.objects.filter(issued_by=user_id).order_by("-created_at")[
        :5
    ]

    activity = [
        {
            "ticket_id": ticket.id,
            "status": ticket.status,
            "fine_amount": ticket.fine_amount,
            "created_at": ticket.created_at,
        }
        for ticket in recent_tickets
    ]

    return JsonResponse(activity, safe=False)

@api_view(["GET"])
def get_All_tickets(request, user_id):
    recent_tickets = Ticket.objects.filter(issued_by=user_id).order_by("-created_at")
    serializer = TicketSerializer2(recent_tickets, many=True)
    return Response(serializer.data)

class LogoutAPIView(APIView):
    def post(self, request):
        return Response(
            {"message": "Logged out successfully"}, status=status.HTTP_200_OK
        )


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        total_tickets = Ticket.objects.filter(issued_by=user).count()
        resolved_tickets = Ticket.objects.filter(
            issued_by=user, status="Resolved"
        ).count()
        pending_tickets = total_tickets - resolved_tickets

        return Response(
            {
                "firstname": user.firstname,
                "lastname": user.lastname,
                "email": user.emailAddress,
                "mobile_number": user.mobile_number,
                "total_tickets": total_tickets,
                "resolved_tickets": resolved_tickets,
                "pending_tickets": pending_tickets,
            }
        )


@api_view(["POST"])
def add_ticket(request):
    try:
        serializer = TicketSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Ticket added successfully"}, status=status.HTTP_201_CREATED
            )
        else:
            print("Validation errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        # Log the exception
        print(f"Error in add_ticket: {str(e)}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def search_tickets(request):
    try:
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        if not start_date or not end_date:
            return Response(
                {"error": "Start date and end date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Convert strings to datetime
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        # Filter tickets between the date range
        tickets = Ticket.objects.filter(created_at__date__range=[start, end])

        serializer = TicketSerializer(tickets, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def process_payment(request):
    try:
        ticket_id = request.data.get("ticket_id")
        if not ticket_id:
            return Response(
                {"error": "Ticket ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        ticket = Ticket.objects.filter(id=ticket_id).first()
        if not ticket:
            return Response(
                {"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND
            )

        ticket.status = "Resolved"
        ticket.save()

        return Response(
            {"message": "Payment processed successfully, ticket resolved"},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def file_dispute(request):
    try:
        ticket_id = request.data.get("ticket_id")
        dispute_reason = request.data.get("reason")

        if not ticket_id or not dispute_reason:
            return Response(
                {"error": "Ticket ID and dispute reason are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ticket = Ticket.objects.filter(id=ticket_id).first()
        if not ticket:
            return Response(
                {"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND
            )

        ticket.status = "Disputed"
        ticket.save()

        return Response(
            {"message": "Dispute filed successfully"}, status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def get_active_tickets(request, user_id):
    user = get_object_or_404(User, id=user_id)

    active_tickets = Ticket.objects.filter(user_id=user, status="Pending")

    tickets_data = []
    for ticket in active_tickets:
        tickets_data.append(
            {
                "id": ticket.id,
                "plate_number": ticket.plate_number,
                "violation": ticket.violation_details.name,
                "fine_amount": ticket.fine_amount,
                "created_at": ticket.created_at,
                "due_date": ticket.due_date,
            }
        )

    return JsonResponse({"active_tickets": tickets_data})


@api_view(["GET"])
def admin_dashboard(request):
    total_tickets = Ticket.objects.count()
    resolved_tickets = Ticket.objects.filter(status="Resolved").count()
    pending_tickets = Ticket.objects.filter(status="Pending").count()

    return Response(
        {
            "total_tickets": total_tickets,
            "resolved_tickets": resolved_tickets,
            "pending_tickets": pending_tickets,
        }
    )


@api_view(["GET"])
def get_drivers(request):
    drivers = User.objects.filter(role="Driver")
    driver_data = [
        {"id": driver.id, "firstname": driver.firstname, "lastname": driver.lastname}
        for driver in drivers
    ]
    total_tickets = Ticket.objects.count()

    return Response({"total_tickets": total_tickets, "drivers": driver_data})


@api_view(["PUT"])
def update_ticket(request, ticket_id):
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        data = request.data
        for field, value in data.items():
            setattr(ticket, field, value)
        ticket.save()
        return Response(
            {"message": "Ticket updated successfully"}, status=status.HTTP_200_OK
        )
    except Ticket.DoesNotExist:
        return Response({"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def get_violations(request):
    violations = Violation.objects.all()
    violation_list = [
        {
            "id": violation.id,
            "name": violation.name,
            "penalty_amount": violation.penalty_amount,
        }
        for violation in violations
    ]
    return Response(violation_list)


"""----------------------------------------WEB----------------------------------------"""


def admin_register(request):
    if request.method == "POST":
        firstname = request.POST.get("firstname")
        lastname = request.POST.get("lastname")
        password = request.POST.get("password")
        username = request.POST.get("username")
        confirm_password = request.POST.get("confirm_password")
        mobile_number = request.POST.get("mobile_number")

        if not firstname or not lastname or not password or not mobile_number:
            messages.error(request, "All fields are required.")
            return redirect("admin_register")
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("admin_register")

        user = User(
            firstname=firstname,
            lastname=lastname,
            username=username,
            mobile_number=mobile_number,
        )
        user.set_password(password)
        user.save()

        messages.success(request, "Registration successful. You can now log in.")
        return redirect("admin_login")

    return render(request, "./admin/admin_register.html")


def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                request.session["user_id"] = user.id
                return redirect("admin_dashboard")
            else:
                messages.error(request, "Invalid username or password.")
        except User.DoesNotExist:
            messages.error(request, "Invalid username or password.")

    return render(request, "./admin/admin_login.html")


def admin_dashboard(request):

    total_users = User.objects.count()

    last_month = datetime.now() - timedelta(days=30)
    prev_total_users = User.objects.filter(date_joined__lt=last_month).count()
    user_change = calculate_percentage_change(prev_total_users, total_users)

    total_drivers = User.objects.filter(role="Driver").count()
    prev_drivers = User.objects.filter(
        role="Driver", date_joined__lt=last_month
    ).count()
    driver_change = calculate_percentage_change(prev_drivers, total_drivers)

    total_police = User.objects.filter(role="Police").count()
    prev_police = User.objects.filter(role="Police", date_joined__lt=last_month).count()
    police_change = calculate_percentage_change(prev_police, total_police)

    total_tickets = Ticket.objects.count()
    prev_tickets = Ticket.objects.filter(created_at__lt=last_month).count()
    ticket_change = calculate_percentage_change(prev_tickets, total_tickets)

    total_pending_tickets = Ticket.objects.filter(status="Pending").count()
    prev_pending = Ticket.objects.filter(
        status="Pending", created_at__lt=last_month
    ).count()
    pending_change = calculate_percentage_change(prev_pending, total_pending_tickets)

    total_resolved_tickets = Ticket.objects.filter(status="Resolved").count()
    prev_resolved = Ticket.objects.filter(
        status="Resolved", created_at__lt=last_month
    ).count()
    resolved_change = calculate_percentage_change(prev_resolved, total_resolved_tickets)

    total_disputed_tickets = Ticket.objects.filter(status="Disputed").count()
    prev_disputed = Ticket.objects.filter(
        status="Disputed", created_at__lt=last_month
    ).count()
    disputed_change = calculate_percentage_change(prev_disputed, total_disputed_tickets)

    total_disputes = Dispute.objects.count()
    prev_disputes = Dispute.objects.filter(created_at__lt=last_month).count()
    dispute_change = calculate_percentage_change(prev_disputes, total_disputes)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    all_months = OrderedDict()
    current_date = start_date.replace(day=1)
    while current_date <= end_date:
        month_key = current_date.strftime("%b %Y")
        all_months[month_key] = 0
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)

    violations_per_month = (
        Ticket.objects.filter(created_at__range=[start_date, end_date])
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    for item in violations_per_month:
        month_key = item["month"].strftime("%b %Y")
        all_months[month_key] = item["count"]

    formatted_violations = [
        {"month": month, "count": count} for month, count in all_months.items()
    ]

    recent_activities = []

    recent_tickets = Ticket.objects.order_by("-created_at")[:3]
    for ticket in recent_tickets:
        recent_activities.append(
            {
                "type": "ticket",
                "title": f"New {ticket.violation_details} ticket issued",
                "time": ticket.created_at,
                "icon": "fa-ticket-alt",
                "color": "var(--primary-color)",
            }
        )

    recent_disputes = Dispute.objects.order_by("-created_at")[:2]
    for dispute in recent_disputes:
        recent_activities.append(
            {
                "type": "dispute",
                "title": f"Dispute opened for ticket #{dispute.ticket.id}",
                "time": dispute.created_at,
                "icon": "fa-gavel",
                "color": "var(--warning-color)",
            }
        )

    recent_activities.sort(key=lambda x: x["time"], reverse=True)
    recent_activities = recent_activities[:5]

    context = {
        "total_users": total_users,
        "user_change": user_change,
        "abs_user_change": abs(user_change),
        "total_drivers": total_drivers,
        "driver_change": driver_change,
        "abs_driver_change": abs(driver_change),
        "total_police": total_police,
        "police_change": police_change,
        "abs_police_change": abs(police_change),
        "total_tickets": total_tickets,
        "ticket_change": ticket_change,
        "abs_ticket_change": abs(ticket_change),
        "total_pending_tickets": total_pending_tickets,
        "pending_change": pending_change,
        "abs_pending_change": abs(pending_change),
        "total_resolved_tickets": total_resolved_tickets,
        "resolved_change": resolved_change,
        "abs_resolved_change": abs(resolved_change),
        "total_disputed_tickets": total_disputed_tickets,
        "disputed_change": disputed_change,
        "abs_dispute_change": abs(dispute_change),
        "total_disputes": total_disputes,
        "dispute_change": dispute_change,
        "violations_per_month": formatted_violations,
        "recent_activities": recent_activities,
    }
    return render(request, "./admin/admin_dashboard.html", context)


def calculate_percentage_change(old_value, new_value):
    if old_value == 0:
        return 0
    return round(((new_value - old_value) / old_value) * 100)


def admin_logout(request):
    request.session.flush()
    messages.success(request, "You have successfully logged out.")
    return redirect("admin_login")


from django.core.paginator import Paginator
from django.db.models import Q


def admin_disputes(request):
    disputes_list = (
        Dispute.objects.select_related("ticket__violation_details", "filed_by")
        .all()
        .order_by("-created_at")
    )

    search_query = request.GET.get("search", "")
    if search_query:
        disputes_list = disputes_list.filter(
            Q(id__icontains=search_query)
            | Q(ticket__id__icontains=search_query)
            | Q(filed_by__firstname__icontains=search_query)
            | Q(filed_by__lastname__icontains=search_query)
            | Q(ticket__violation_details__name__icontains=search_query)
            | Q(reason__icontains=search_query)
        )

    status_filter = request.GET.get("status", "")
    if status_filter:
        disputes_list = disputes_list.filter(ticket__status=status_filter)

    paginator = Paginator(disputes_list, 10)
    page_number = request.GET.get("page")
    disputes = paginator.get_page(page_number)

    status_choices = Ticket.STATUS_CHOICES

    context = {
        "disputes": disputes,
        "search_query": search_query,
        "status_filter": status_filter,
        "status_choices": status_choices,
    }
    return render(request, "./admin/admin_disputes.html", context)


def admin_payments(request):
    return render(request, "./admin/admin_payments.html")


def admin_search(request):
    return render(request, "./admin/admin_search.html")


def admin_tickets(request):
    if request.method == "POST":
        ticket_id = request.POST.get("ticket_id")
        new_status = request.POST.get("status")
        ticket = get_object_or_404(Ticket, id=ticket_id)
        ticket.status = new_status
        ticket.save()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True})
        else:
            messages.success(request, "Ticket status updated successfully!")
            return redirect("admin_tickets")

    tickets_list = Ticket.objects.all().order_by("-created_at")

    search_query = request.GET.get("search", "")
    if search_query:
        tickets_list = tickets_list.filter(
            Q(license_no__icontains=search_query)
            | Q(plate_number__icontains=search_query)
            | Q(user_id__firstname__icontains=search_query)
            | Q(user_id__lastname__icontains=search_query)
            | Q(issued_by__firstname__icontains=search_query)
            | Q(issued_by__lastname__icontains=search_query)
            | Q(location__icontains=search_query)
            | Q(status__icontains=search_query)
        )

    status_filter = request.GET.get("status", "")
    if status_filter:
        tickets_list = tickets_list.filter(status=status_filter)

    paginator = Paginator(tickets_list, 10)
    page_number = request.GET.get("page")
    tickets = paginator.get_page(page_number)

    status_choices = Ticket.STATUS_CHOICES

    context = {
        "tickets": tickets,
        "search_query": search_query,
        "status_filter": status_filter,
        "status_choices": status_choices,
    }
    return render(request, "./admin/admin_tickets.html", context)


def admin_violations(request):
    violations_list = Violation.objects.all().order_by("name")

    search_query = request.GET.get("search", "")
    if search_query:
        violations_list = violations_list.filter(
            Q(name__icontains=search_query) | Q(penalty_amount__icontains=search_query)
        )

    paginator = Paginator(violations_list, 10)
    page_number = request.GET.get("page")
    violations = paginator.get_page(page_number)

    context = {
        "violations": violations,
        "search_query": search_query,
    }
    return render(request, "./admin/admin_violations.html", context)


@csrf_exempt
def add_violation(request):
    if request.method == "POST":
        name = request.POST.get("name")
        penalty_amount = request.POST.get("penalty_amount")

        Violation.objects.create(name=name, penalty_amount=penalty_amount)
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"})


@csrf_exempt
def edit_violation(request, id):
    violation = get_object_or_404(Violation, id=id)
    if request.method == "POST":
        violation.name = request.POST.get("name")
        violation.penalty_amount = request.POST.get("penalty_amount")
        violation.save()
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"})


@csrf_exempt
def delete_violation(request, id):
    violation = get_object_or_404(Violation, id=id)
    violation.delete()
    return JsonResponse({"status": "success"})
