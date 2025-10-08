from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F
from .models import CustomUser, PurchaseOrder, SupplierRequest, Transaction
from .decorators import role_required
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Bill, BillItem, Product, Transaction
from django.db import transaction
from .models import Supplier

User = get_user_model()


# ------------------ AUTH ------------------

def home_view(request):
    return render(request, "home.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if user.role == "admin":
                return redirect("admin_dashboard")
            elif user.role == "staff":
                return redirect("staff_dashboard")
            elif user.role == "supplier":
                if hasattr(user, "supplier_profile") and user.supplier_profile.status == "approved":
                    return redirect("supplier_dashboard")
                else:
                     return redirect("supplier_pending") 
        else:
            messages.error(request, "Invalid username or password.")
    storage = messages.get_messages(request)
    for _ in storage:
        pass 
    return render(request, "login.html")


from .models import CustomUser, Supplier
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.hashers import make_password
from .models import CustomUser, Supplier

def register_view(request):
    role = "staff"  # default role for GET request

    if request.method == "POST":
        role = request.POST.get("role")

        # -------- STAFF REGISTRATION --------
        if role == "staff":
            username = request.POST.get("username_staff")
            password = request.POST.get("password_staff")
            confirm_password = request.POST.get("confirm_password_staff")
            first_name = request.POST.get("first_name")
            last_name = request.POST.get("last_name")
            phone = request.POST.get("phone_staff")
            gender = request.POST.get("gender_staff")

            # Validate passwords
            if password != confirm_password:
                messages.error(request, "Passwords do not match ❌")
                return redirect("register")

            # Check if username exists
            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, "Username already taken ❌")
                return redirect("register")

            # Create staff user
            user = CustomUser.objects.create(
                username=username,
                password=make_password(password),
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                gender=gender,
                role="staff",
            )

            login(request, user)
            messages.success(request, "Staff account created successfully ✅")
            return redirect("staff_dashboard")

        # -------- SUPPLIER REGISTRATION --------
        elif role == "supplier":
            username = request.POST.get("username_supplier")
            password = request.POST.get("password_supplier")
            confirm_password = request.POST.get("confirm_password_supplier")
            phone = request.POST.get("phone_supplier")
            supplier_name = request.POST.get("supplier_name")
            contact_person = request.POST.get("contact_person")
            email = request.POST.get("email_supplier")
            address = request.POST.get("address_supplier")

            # Validate passwords
            if password != confirm_password:
                messages.error(request, "Passwords do not match ❌")
                return redirect("register")

            # Check if username exists
            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, "Username already taken ❌")
                return redirect("register")

            # Create supplier user
            user = CustomUser.objects.create(
                username=username,
                password=make_password(password),
                role="supplier",
                phone=phone,
            )

            # Create supplier profile with pending status
            Supplier.objects.create(
                user=user,
                name=supplier_name,
                contact_person=contact_person,
                phone=phone,
                email=email,
                address=address,
                status="pending",
            )

            login(request, user)
            messages.info(request, "Supplier account created. Waiting for admin approval ⏳")
            return redirect("supplier_pending")

    # -------- GET REQUEST --------
    return render(request, "register.html", {"role": role})





def logout_view(request):
    request.session.pop("request_warning_shown", None)
    logout(request)
    return redirect("login")


# ------------------ ADMIN DASHBOARD ------------------

@login_required
def admin_dashboard(request):

    if request.user.role != "admin":
        return render(request, "unauth.html", status=403)

    pending_suppliers = Supplier.objects.filter(status="pending")
    warning_message = None
    if pending_suppliers.exists() and not request.session.get("request_warning_shown", False):
        count = pending_suppliers.count()
        warning_message = f"⚠️ {count} new supplier request(s) pending approval."
        messages.warning(request, warning_message)
        request.session["request_warning_shown"] = True 

    # Handle stock transaction form
    if request.method == "POST" and "transaction_form" in request.POST:
        product_id = request.POST.get("product")
        transaction_type = request.POST.get("type")
        quantity = int(request.POST.get("quantity", 0))
        remarks = request.POST.get("remarks", "")

        product = get_object_or_404(Product, id=product_id)

        if transaction_type == "in":
            product.stock += quantity
        elif transaction_type == "out":
            if product.stock < quantity:
                messages.error(request, "Not enough stock to remove.")
                return redirect("admin_dashboard")
            product.stock -= quantity

        product.save()

        # Save history
        Transaction.objects.create(
            product=product,
            type=transaction_type,
            quantity=quantity,
            remarks=remarks,
            user=request.user,
        )

        messages.success(request, f"{transaction_type.upper()} recorded for {product.name}")
        return redirect("admin_dashboard")

    # Handle add product form
    if request.method == "POST" and "product_form" in request.POST:
        Product.objects.create(
            name=request.POST.get("name"),
            category=request.POST.get("category"),
            stock=int(request.POST.get("stock", 0)),
            min_stock=int(request.POST.get("min_stock", 5)),
            price=request.POST.get("price"),
            description=request.POST.get("description"),
        )
        messages.success(request, "✅ Product added successfully!")
        return redirect("admin_dashboard")

    # Dashboard data
    total_products = Product.objects.count()
    total_stock = Product.objects.aggregate(total=Sum("stock"))["total"] or 0
    low_stock_products = Product.objects.filter(stock__lte=F("min_stock"))
    recent_transactions = Transaction.objects.order_by("-date")[:5]
    transactions_count = Transaction.objects.count()
    active_users = User.objects.filter( is_active=True,role__in=['staff', 'supplier']).count()
    chart_labels = list(Product.objects.values_list("name", flat=True))
    chart_data = list(Product.objects.values_list("stock", flat=True))
    context = {
        "total_products": total_products,
        "total_stock": total_stock,
        "low_stock_products": low_stock_products,
        "recent_transactions": recent_transactions,
        "transactions_count": transactions_count,
        "active_users": active_users,
        "products": Product.objects.all(),
        "chart_labels": chart_labels,
        "chart_data": chart_data,
        "warning_message": warning_message, 
        "pending_suppliers": pending_suppliers, 
    }
    return render(request, "admin_dashboard.html", context)

@login_required
@role_required(["admin"])
def admin_supplier_requests(request):
    requests = SupplierRequest.objects.all().order_by("-created_at")
    return render(request, "admin_supplier_requests.html", {"requests": requests})


from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import SupplierRequest, Product, Transaction
from .decorators import role_required


@login_required
@role_required(["admin"])
def approve_supplier_request(request, request_id):
    """Approve supplier request and update stock + transaction"""
    req = get_object_or_404(SupplierRequest, id=request_id)

    if req.status != "pending":
        messages.warning(request, f"⚠️ Request for '{req.product_name}' is already {req.status}.")
        return redirect("admin_supplier_requests")

    # ✅ Mark as approved
    req.status = "approved"
    req.save()

    # ✅ Add or update product
    product, created = Product.objects.get_or_create(
        name=req.product_name,
        defaults={
            "category": "Supplier",
            "stock": req.quantity,
            "price": req.price_per_unit,
            "description": req.description or "",
        },
    )

    if not created:
        product.stock += req.quantity
        product.price = req.price_per_unit  # Optional: keep price updated
        if req.description:
            product.description = req.description
        product.save()

    # ✅ Record transaction
    Transaction.objects.create(
        product=product,
        type="in",
        quantity=req.quantity,
        user=request.user,
        remarks=f"Supplier '{req.supplier.name}' supplied {req.quantity} unit(s)."
    )

    # ✅ Success message and reset session warning
    messages.success(request, f"✅ '{req.product_name}' approved and stock updated successfully!")
    request.session["request_warning_shown"] = False

    return redirect("admin_supplier_requests")


@login_required
@role_required(["admin"])
def reject_supplier_request(request, request_id):
    """Reject supplier request"""
    req = get_object_or_404(SupplierRequest, id=request_id)

    if req.status != "pending":
        messages.warning(request, f"⚠️ Request for '{req.product_name}' is already {req.status}.")
        return redirect("admin_supplier_requests")

    req.status = "rejected"
    req.save()

    messages.error(request, f"❌ Supplier request for '{req.product_name}' has been rejected.")
    return redirect("admin_supplier_requests")

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Supplier, SupplierRequest
from .decorators import role_required

# @login_required
# @role_required(["admin", "staff"])
def request_product(request):
    # show only approved suppliers
    suppliers = Supplier.objects.filter(status="approved")

    if request.method == "POST":
        supplier_id = request.POST.get("supplier")
        supplier = get_object_or_404(Supplier, id=supplier_id)

        # Create supplier request (not adding product yet)
        SupplierRequest.objects.create(
            supplier=supplier,
            product_name=request.POST.get("product_name"),
            description=request.POST.get("description"),
            price_per_unit=request.POST.get("price_per_unit"),
            quantity=request.POST.get("quantity"),
        )

        messages.success(request, "📦 Product request submitted successfully!")
        return redirect("admin_dashboard")

    return render(request, "request_product.html", {"suppliers": suppliers})

# ------------------ PRODUCT MANAGEMENT ------------------

@login_required
def add_product(request):
    if request.method == "POST":
        Product.objects.create(
            name=request.POST.get("name"),
            category=request.POST.get("category"),
            stock=request.POST.get("stock"),
            price=request.POST.get("price"),
            description=request.POST.get("description"),
            min_stock=request.POST.get("min_stock", 5),
        )
        messages.success(request, "✅ Product added successfully!")
        return redirect("admin_dashboard")
    return render(request, "add_product.html")


@login_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == "POST":
        product.name = request.POST.get("name")
        product.category = request.POST.get("category")
        product.stock = request.POST.get("stock")
        product.price = request.POST.get("price")
        product.description = request.POST.get("description")
        product.min_stock = request.POST.get("min_stock", 5)
        product.save()
        messages.success(request, "✅ Product updated successfully")
        return redirect("admin_dashboard")
    return render(request, "edit_product.html", {"product": product})


@login_required
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    messages.success(request, "🗑 Product deleted successfully")
    return redirect("admin_dashboard")


# ------------------ TRANSACTIONS HISTORY ------------------

@login_required
@role_required(['admin'])
def stock_history(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    transactions = product.transactions.order_by("-date")
    return render(request, "stock_history.html", {
        "product": product,
        "transactions": transactions
    })

@login_required
def transactions_view(request):
    # ✅ Get all transactions
    transactions = Transaction.objects.select_related("product", "user").order_by("-date")

    # ✅ Filtering
    transaction_type = request.GET.get("type")
    search_query = request.GET.get("q")

    if transaction_type in ["in", "out"]:
        transactions = transactions.filter(type=transaction_type)

    if search_query:
        transactions = transactions.filter(
            Q(product__name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(remarks__icontains=search_query)
        )

    # ✅ Pagination
    paginator = Paginator(transactions, 10)  # 10 per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "transactions.html", {
        "page_obj": page_obj,
        "transaction_type": transaction_type,
        "search_query": search_query,
    })


# ------------------ USER MANAGEMENT ------------------

@login_required
def manage_users(request):
    role = request.GET.get("role")
    users = CustomUser.objects.exclude(role="admin")
    if role:
        users = users.filter(role=role)
    return render(request, "manage_users.html", {"users": users})


# @login_required
# def edit_user(request, user_id):
#     user = get_object_or_404(CustomUser, id=user_id)
#     if user.role == "admin":
#         messages.error(request, "❌ You cannot edit Admin users")
#         return redirect("manage_users")

#     if request.method == "POST":
#         new_role = request.POST.get("role")
#         user.role = new_role
#         user.save()
#         messages.success(request, f"✅ {user.username}'s role updated to {new_role}")
#         return redirect("manage_users")

#     return render(request, "edit_user.html", {"user": user})




@login_required
def delete_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    user.delete()
    messages.success(request, "🗑 User deleted successfully")
    return redirect("manage_users")


# ------------------ STAFF DASHBOARD ------------------

@login_required
@role_required(['staff'])
def staff_dashboard(request):
    # Show product & transaction summary for staff
    total_products = Product.objects.count()
    total_stock = Product.objects.aggregate(total=Sum('stock'))['total'] or 0
    my_transactions = Transaction.objects.filter(user=request.user).order_by('-date')[:5]

    # 🔹 Current product list (to verify updated stock after billing)
    products = Product.objects.all().order_by("name")

    # 🔹 Low stock alerts
    low_stock_products = Product.objects.filter(stock__lte=F("min_stock"))

    context = {
         "total_products": total_products,
        "total_stock": total_stock,
        "my_transactions": my_transactions,
        "products": products,
        "low_stock_products": low_stock_products,
    }
    return render(request, "staff_dashboard.html", context)

from .models import Product, Transaction, Bill, BillItem


@login_required
@role_required(['staff'])
def new_bill(request):
    if request.method == "POST":
        customer_name = request.POST.get("customer_name")
        selected_products = request.POST.getlist("product_ids")  # id:index

        if not customer_name or not selected_products:
            messages.error(request, "Please enter a customer name and select at least one product")
            return redirect("new_bill")

        try:
            with transaction.atomic():
                bill = Bill.objects.create(customer_name=customer_name, created_by=request.user)

                for item in selected_products:
                    if ":" not in item:
                        continue
                    pid, idx = item.split(":", 1)
                    qty_str = request.POST.get(f"quantity_{idx}", "0")
                    try:
                        qty = int(qty_str)
                    except ValueError:
                        qty = 0
                    if qty <= 0:
                        continue

                    product = Product.objects.select_for_update().get(id=pid)  # ✅ lock row
                    if product.stock < qty:
                        raise ValueError(
                            f"Not enough stock for {product.name}. Available: {product.stock}, Requested: {qty}"
                        )

                    # Create BillItem
                    BillItem.objects.create(
                        bill=bill,
                        product=product,
                        quantity=qty,
                        price=product.price
                    )

                    # Reduce stock safely
                    product.stock = F('stock') - qty
                    product.save(update_fields=['stock'])

                    # Refresh to get the actual integer value
                    product.refresh_from_db()

                    # Record transaction
                    Transaction.objects.create(
                        product=product,
                        type="out",
                        quantity=qty,
                        user=request.user,
                        remarks=f"Sale to {customer_name} on Bill #{bill.id}"
                    )

            messages.success(request, f"Bill #{bill.id} created successfully ✅")
            return redirect("staff_dashboard")
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {e}")

    # GET request
    try:
        last_bill = Bill.objects.latest("id")
        next_invoice_number = last_bill.id + 1
    except Bill.DoesNotExist:
        next_invoice_number = 1

    products = Product.objects.all()
    return render(request, "new_bill.html", {
        "products": products,
        "invoice_number": next_invoice_number
    })


@login_required
@role_required(['staff'])
# def my_bills(request):
#     bills = Bill.objects.filter(created_by=request.user).order_by("-date")
#     return render(request, "my_bills.html", {"bills": bills})

def my_bills_list(request):
    
    bills = Bill.objects.all().order_by('-date')  # Order by creation date, newest first
    return render(request, "bill_list.html", {"bills": bills})



# ------------------ supplier DASHBOARD ------------------


@login_required
@role_required(["supplier"])
def supplier_dashboard(request):
    supplier = Supplier.objects.get(user=request.user)

    # Existing order-related stats
    total_orders = supplier.orders.count()
    pending_orders = supplier.orders.filter(status="pending").count()
    delivered_orders = supplier.orders.filter(status="delivered").count()
    recent_orders = supplier.orders.order_by("-created_at")[:5]

    # 🆕 New: Product requests related to this supplier
    product_requests = supplier.requests.all().order_by("-created_at")

    return render(request, "supplier_dashboard.html", {
        "supplier": supplier,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "delivered_orders": delivered_orders,
        "recent_orders": recent_orders,
        "product_requests": product_requests,  # added context
    })



@login_required
@role_required(["supplier"])
def update_order_status(request, order_id, status):
    order = get_object_or_404(PurchaseOrder, id=order_id, supplier__user=request.user)
    order.status = status
    order.save()
    messages.success(request, f"Order #{order.id} marked as {status} ✅")
    return redirect("supplier_dashboard")



@login_required
def supplier_management(request):
    if request.user.role != "admin":
        return render(request, "unauthorized.html", status=403)

    suppliers = Supplier.objects.all().order_by("-created_at")
    return render(request, "supplier_management.html", {"suppliers": suppliers})

@login_required
@role_required(["admin"])
def approve_supplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)
    supplier.status = "approved"
    supplier.save()
    messages.success(request, f"Supplier {supplier.name} approved ✅")
    request.session["request_warning_shown"] = False
    return redirect("supplier_management")

@login_required
@role_required(["admin"])
def reject_supplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)
    supplier.status = "rejected"
    supplier.save()
    messages.error(request, f"Supplier {supplier.name} rejected ❌")
    request.session["request_warning_shown"] = False
    return redirect("supplier_management")

@login_required
@role_required(["supplier"])
def supplier_pending(request):
    supplier = getattr(request.user, "supplier_profile", None)

    if supplier and supplier.status == "approved":
        return redirect("supplier_dashboard")  # already approved
    elif supplier and supplier.status == "rejected":
        message = "❌ Your supplier account has been rejected. Contact admin for details."
    else:
        message = "⏳ Your supplier account is pending approval. Please wait until an admin approves it."

    return render(request, "supplier_pending.html", {"status": supplier.status})

@login_required
@role_required(["supplier"])
def supplier_orders(request):
    supplier = Supplier.objects.get(user=request.user)
    orders = supplier.orders.order_by("-created_at")  # all orders for this supplier
    return render(request, "supplier_orders.html", {"orders": orders})


# # ✅ Supplier Payments (dummy for now, will extend with Payment model)
# @login_required
# @role_required(["supplier"])
# def supplier_payments(request):
#     supplier = Supplier.objects.get(user=request.user)
#     payments = supplier.orders.filter(status="delivered")

#     return render(request, "supplier_payments.html", {"payments": payments})

@login_required
@role_required(["supplier"])
def supplier_request_product(request):
    if request.method == "POST":
        supplier = getattr(request.user, "supplier_profile", None)
        if not supplier:
            messages.error(request, "Supplier profile not found ❌")
            return redirect("supplier_request_product")

        product_name = request.POST.get("product_name")
        description = request.POST.get("description", "")
        price = request.POST.get("price")
        quantity = request.POST.get("quantity")

        if not product_name or not price or not quantity:
            messages.error(request, "All fields (name, price, quantity) are required ❌")
            return redirect("supplier_request_product")

        try:
            SupplierRequest.objects.create(
                supplier=supplier,
                product_name=product_name,
                description=description,
                price_per_unit=float(price),
                quantity=int(quantity),
            )
            messages.success(request, "Request sent to admin ✅")
            request.session["new_supplier_request"] = True
            return redirect("supplier_requests")
        except Exception as e:
            messages.error(request, f"Error submitting request: {e}")

    return render(request, "supplier_request_product.html")


@login_required
@role_required(["supplier"])
def supplier_requests(request):
    supplier = getattr(request.user, "supplier_profile", None)
    if not supplier:
        return render(request, "unauthorized.html", status=403)

    requests = SupplierRequest.objects.filter(supplier=supplier).order_by("-created_at")
    return render(request, "supplier_requests.html", {"requests": requests})

@login_required
@role_required(["supplier", "admin"])  # Only supplier or admin can approve
def approve_request(request, request_id):
    if request.method == "POST":
        req = get_object_or_404(SupplierRequest, id=request_id)

        # Mark the request as approved
        req.status = "approved"
        req.save()

        # Update existing product or create new one
        product, created = Product.objects.get_or_create(
            name=req.product_name,
            defaults={
                "category": req.product_name,  # You can set category if needed
                "stock": req.quantity,
                "price": req.price_per_unit,
                "description": req.description or "",
                "min_stock": 5,
            }
        )

        if not created:
            # If product exists, just increase the stock
            product.stock += req.quantity
            # Optionally update price if you want latest supplier price
            product.price = req.price_per_unit
            product.save()

        messages.success(request, f"✅ '{req.product_name}' approved and stock updated.")
    
    return redirect("supplier_dashboard") 


@login_required
def reject_request(request, request_id):
    if request.method == "POST":
        supplier = getattr(request.user, "supplier_profile", None)
        if not supplier:
            return render(request, "unauthorized.html", status=403)

        req = get_object_or_404(SupplierRequest, id=request_id, supplier=supplier)
        req.status = "rejected"
        req.save()
        messages.error(request, f"❌ Product '{req.product_name}' has been rejected.")
    return redirect("supplier_dashboard")



