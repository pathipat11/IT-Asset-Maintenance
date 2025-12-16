from django.urls import path
from . import views, stock_views
from .exports import export_assets_csv, export_tickets_csv, export_parts_csv, export_movements_csv


app_name = "core"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),

    # Asset
    path("assets/", views.AssetListView.as_view(), name="asset_list"),
    path("assets/new/", views.AssetCreateView.as_view(), name="asset_create"),
    path("assets/<int:pk>/", views.AssetDetailView.as_view(), name="asset_detail"),
    path("assets/<int:pk>/edit/", views.AssetUpdateView.as_view(), name="asset_update"),
    path("assets/<int:pk>/delete/", views.AssetDeleteView.as_view(), name="asset_delete"),

    # Ticket
    path("tickets/", views.TicketListView.as_view(), name="ticket_list"),
    path("tickets/new/", views.TicketCreateView.as_view(), name="ticket_create"),
    path("tickets/<int:pk>/", views.TicketDetailView.as_view(), name="ticket_detail"),
    path("tickets/<int:pk>/edit/", views.TicketUpdateView.as_view(), name="ticket_update"),
    path("tickets/<int:pk>/delete/", views.TicketDeleteView.as_view(), name="ticket_delete"),
    
    path("export/assets.csv", export_assets_csv, name="export_assets_csv"),
    path("export/tickets.csv", export_tickets_csv, name="export_tickets_csv"),
    
    path("export/parts.csv", export_parts_csv, name="export_parts_csv"),
    path("export/movements.csv", export_movements_csv, name="export_movements_csv"),
]

urlpatterns += [
    path("tickets/<int:pk>/assign-to-me/", views.TicketAssignToMeView.as_view(), name="ticket_assign_to_me"),
    path("tickets/<int:pk>/start/", views.TicketStartView.as_view(), name="ticket_start"),
    path("tickets/<int:pk>/resolve/", views.TicketResolveView.as_view(), name="ticket_resolve"),
    path("tickets/<int:pk>/close/", views.TicketCloseView.as_view(), name="ticket_close"),
    
    path("parts/", stock_views.PartListView.as_view(), name="part_list"),
    path("parts/new/", stock_views.PartCreateView.as_view(), name="part_create"),
    path("parts/<int:pk>/", stock_views.PartDetailView.as_view(), name="part_detail"),
    path("parts/<int:pk>/edit/", stock_views.PartUpdateView.as_view(), name="part_update"),
    path("parts/<int:pk>/delete/", stock_views.PartDeleteView.as_view(), name="part_delete"),
    path("parts/low-stock/", stock_views.LowStockListView.as_view(), name="low_stock"),
]
