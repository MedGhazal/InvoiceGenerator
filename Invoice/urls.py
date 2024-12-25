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
from django.urls import path
from .views import (
    download_invoice,
    delete_project,
    delete_fee,
    modify_invoice,
    modify_project,
    modify_fee,
    add_projectAndFeesToInvoice,
    add_feesToProject,
    InvoiceDetailView,
    InvoiceListView,
)

app_name = 'Invoice'
urlpatterns = [
    path('', InvoiceListView.as_view(), name='index'),
    path('preview/<slug:pk>', InvoiceDetailView.as_view(), name='preview'),
    path('download/<int:invoice>', download_invoice, name='download'),
    path('modify/<int:invoice>', modify_invoice, name='modify'),
    path('modifyProject/<int:project>', modify_project, name='modifyProject'),
    path('modifyFee/<int:fee>', modify_fee, name='modifyFee'),
    path(
        'addFeesToProject/<int:project>',
        add_feesToProject,
        name='addFeesToProject',
    ),
    path(
        'addProjectAndFees/<int:invoice>',
        add_projectAndFeesToInvoice,
        name="addProjectAndFeesToInvoice",
    ),
    path('deleteProject/<int:project>', delete_project, name='deleteProject'),
    path('deleteFee/<int:fee>', delete_fee, name='deleteFee'),
]
