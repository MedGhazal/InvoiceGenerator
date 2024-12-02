from django.contrib.admin import (
    register,
    ModelAdmin,
    StackedInline,
    SimpleListFilter,
)
from .models import (
    Product,
    Charge,
    Supplier,
    Sale,
    ChargeProduct,
    SaleProduct,
)
from django.utils.translation import gettext as _
from rangefilter.filter import (
    DateRangeFilter,
)


@register(Product)
class ProductAdmin(ModelAdmin):
    list_display = (
        'name',
        'description',
        'price',
        'count',
    )
    # list_filter = (
    #     ('count', NumericRangeFilter),
    # )
    search_fields = ('name',)


class ChargeProductStackedInline(StackedInline):
    model = ChargeProduct
    min_num = 1
    extra = 0
    autocomplete_fields = ('product',)


class SupplierChargeSimpleListFilter(SimpleListFilter):

    title = _('SUPPLIER')

    def lookups(self, request, chargeAdmin):
        suppliers = [
            (supplier.id, supplier.name)
            for supplier in Supplier.objects.all()
        ]
        suppliers.append((-1, _('NONE'),))
        return suppliers

    def queryset(self, request, queryset):
        return queryset


@register(Charge)
class ChargeAdmin(ModelAdmin):
    list_display = (
        'entryDate',
        'amount',
    )
    list_filter = (
        ('entryDate', DateRangeFilter),
        'supplier',
    )
    inlines = [
        ChargeProductStackedInline,
    ]
    fields = [
        'supplier',
        'entryDate',
        'amount',
    ]
    autocomplete_fields = ('supplier',)

    def save_model(self, request, charge, form, change):
        charge.save()

    def delete_queryset(self, request, queryset):
        for charge in queryset:
            for product in charge.products.all():
                for productCharge in ChargeProduct.objects.filter(
                    product=product,
                    charge=charge,
                ):
                    product.count -= productCharge.count
                product.save()
            charge.delete()

    def delete_model(self, request, charge):
        for product in charge.products.all():
            for productCharge in ChargeProduct.objects.filter(
                product=product,
                charge=charge,
            ):
                product.count -= productCharge.count
            product.save()
        charge.delete()

    def save_related(self, request, form, formsets, change):
        form.save_m2m()
        for formset in formsets:
            if change:
                chargeProducts = formset.cleaned_data
                for chargeProduct in chargeProducts:
                    if chargeProduct is not None:
                        product = chargeProduct['product']
                        if chargeProduct['id'] is not None:
                            product.count -= chargeProduct['id'].count
                        product.count += chargeProduct['count']
                        product.save()
            else:
                chargeProducts = formset.cleaned_data
                for chargeProduct in chargeProducts:
                    product = chargeProduct['product']
                    product.count += chargeProduct['count']
                    product.save()
            self.save_formset(request, form, formset, change=change)


@register(Supplier)
class Supplier(ModelAdmin):
    search_fields = ('name',)


class SaleProductStackedInline(StackedInline):
    model = SaleProduct
    min_num = 1
    extra = 0
    autocomplete_fields = ('product',)


@register(Sale)
class SaleAdmin(ModelAdmin):
    inlines = [SaleProductStackedInline]
    autocomplete_fields = ('invoicee',)
