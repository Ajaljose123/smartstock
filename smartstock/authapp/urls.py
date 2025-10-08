from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'), 
    path('login/',views.login_view, name='login'),
    path('logout/',views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('staff-dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path("new-bill/", views.new_bill, name="new_bill"),
    path('my_bills/', views.my_bills_list, name='bill_list'),
    path("edit-product/<int:product_id>/", views.edit_product, name="edit_product"),
    path("delete-product/<int:product_id>/", views.delete_product, name="delete_product"),
    path("add-product/", views.add_product, name="add_product"),
    path("request-product/", views.request_product, name="request_product"),
    path("manage-users/", views.manage_users, name="manage_users"),
    # path("edit-user/<int:user_id>/", views.edit_user, name="edit_user"),
    path("delete-user/<int:user_id>/", views.delete_user, name="delete_user"),
    path("stock-history/<int:product_id>/", views.stock_history, name="stock_history"),
    path("transactions/", views.transactions_view, name="transactions"),
    path("supplier/dashboard/", views.supplier_dashboard, name="supplier_dashboard"),
    path("supplier-request/<int:request_id>/approve/", views.approve_request, name="approve_request"),
    path("supplier-request/<int:request_id>/reject/", views.reject_request, name="reject_request"),
    path("supplier/order/<int:order_id>/<str:status>/", views.update_order_status, name="update_order_status"),
    path("suppliers/", views.supplier_management, name="supplier_management"),
    path("suppliers/approve/<int:supplier_id>/", views.approve_supplier, name="approve_supplier"),
    path("suppliers/reject/<int:supplier_id>/", views.reject_supplier, name="reject_supplier"),
    path("supplier/pending/", views.supplier_pending, name="supplier_pending"),
    path("supplier/orders/", views.supplier_orders, name="supplier_orders"),
    path("supplier/request/", views.supplier_request_product, name="supplier_request_product"),
    path("supplier/requests/", views.supplier_requests, name="supplier_requests"),
    path("dashboard/supplier-requests/", views.admin_supplier_requests, name="admin_supplier_requests"),
    path("dashboard/supplier-requests/<int:request_id>/approve/", views.approve_supplier_request, name="approve_supplier_request"),
    path("dashboard/supplier-requests/<int:request_id>/reject/", views.reject_supplier_request, name="reject_supplier_request"),


    
]