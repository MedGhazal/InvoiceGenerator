"""
URL configuration for InvoiceGenerator project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, register_converter
from .views import (
    InvoiceeListView,
    PrivateInvoiceeListView,
    InvoiceeDetailView,
    InvoiceeCreateView,
    InvoiceeUpdateView,
    PrivateInvoiceeCreateView,
)

from Core.views import DateConverter


register_converter(DateConverter, 'date')
app_name = 'Invoicee'
urlpatterns = [
    path('', InvoiceeListView.as_view(), name='invoicees'),
    path('private', PrivateInvoiceeListView.as_view(), name='pinvoicees'),
    path('detail/<slug:pk>', InvoiceeDetailView.as_view(), name='invoicee'),
    path(
        'addInvoicee',
        InvoiceeCreateView.as_view(),
        name='add-invoicee',
    ),
    path(
        'addPrivateInvoicee',
        PrivateInvoiceeCreateView.as_view(),
        name='add-private-invoicee',
    ),
    path(
        'modify/<slug:pk>',
        InvoiceeUpdateView.as_view(),
        name='modify-invoicee',
    ),
    path(
        'addInvoicee',
        InvoiceeCreateView.as_view(),
        name='add-invoicee',
    ),
]
