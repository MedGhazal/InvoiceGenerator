from django.urls import path, register_converter
from .views import (
    download_invoice,
    delete_project,
    delete_fee,
    modify_invoice,
    modify_project,
    modify_fee,
    add_projectAndFeesToInvoice,
    add_feesToProject,
    create_creditNoteOfInvoice,
    add_invoice,
    validate_invoice,
    delete_invoice,
    add_draft,
    invoice_estimate,
    InvoiceDetailView,
    InvoiceListView,
)

from Core.views import DateConverter


register_converter(DateConverter, 'date')
app_name = 'Invoice'
urlpatterns = [
    path('', InvoiceListView.as_view(), name='index'),
    path(
        '<int:invoicer>/<int:invoicee>/<date:beginDate>/<date:endDate>',
        InvoiceListView.as_view(),
        name='index',
    ),
    path('addInvoice/', add_invoice, name='add-invoice'),
    path('deleteInvoice/<int:invoice>', delete_invoice, name='delete-invoice'),
    path(
        'invoiceEstimate/<int:invoice>',
        invoice_estimate,
        name='invoice-estimate',
    ),
    path('addDraft/', add_draft, name='add-draft'),
    path(
        'invoiceValidate/<int:invoice>',
        validate_invoice,
        name='validate-invoice',
    ),
    path(
        'createCreditNote/<int:invoice>',
        create_creditNoteOfInvoice,
        name='create-creditNote',
    ),
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
