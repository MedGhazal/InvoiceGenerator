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
    add_invoice_for,
    validate_invoice,
    delete_invoice,
    add_estimate,
    add_estimate_for,
    invoice_estimate,
    delete_payment,
    InvoiceDetailView,
    InvoiceListView,
    EstimateListView,
    CreditNoteListView,
    PaymentCreateView,
    PaymentUpdateView,
    PaymentDetailView,
    PaymentListView,
)

from Core.views import DateConverter


register_converter(DateConverter, 'date')
app_name = 'Invoice'
urlpatterns = [
    path('', InvoiceListView.as_view(), name='index'),
    path('estimates', EstimateListView.as_view(), name='estimates'),
    path('creditNotes', CreditNoteListView.as_view(), name='creditNotes'),
    path(
        '<int:invoicer>/<int:invoicee>/<date:beginDate>/<date:endDate>',
        InvoiceListView.as_view(),
        name='index',
    ),
    path('addInvoice/', add_invoice, name='add-invoice'),
    path('addEstimate/', add_estimate, name='add-estimate'),
    path(
        'addInvoiceFor/<int:invoicee>',
        add_invoice_for,
        name='add-invoice-for',
    ),
    path(
        'addEstimateFor/<int:invoicee>',
        add_estimate_for,
        name='add-estimate-for',
    ),
    path('deleteInvoice/<int:invoice>', delete_invoice, name='delete-invoice'),
    path(
        'invoiceEstimate/<int:invoice>',
        invoice_estimate,
        name='invoice-estimate',
    ),
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
    path('updateFee/<int:fee>', modify_fee, name='updateFee'),
    path('payments', PaymentListView.as_view(), name='payments'),
    path('payment/<slug:pk>', PaymentDetailView.as_view(), name='payment'),
    path('addPayment', PaymentCreateView.as_view(), name='add-payment'),
    path(
        'updatePayment/<slug:pk>',
        PaymentUpdateView.as_view(),
        name='update-payment',
    ),
    path(
        'deletePayment/<int:payment>',
        delete_payment,
        name='delete-payment',
    )
]
