from django.contrib.admin import (
    register,
    ModelAdmin,
    StackedInline,
)
from .models import (
    Product,
    Charge,
    Supplier,
    Sale,
    ChargeProduct,
    SaleProduct,
)


@register(Product)
class ProductAdmin(ModelAdmin):
    search_fields = ('name',)


class ChargeProductStackedInline(StackedInline):
    model = ChargeProduct
    min_num = 1
    extra = 0
    autocomplete_fields = ('product',)


@register(Charge)
class ChargeAdmin(ModelAdmin):
    inlines = [
        ChargeProductStackedInline,
    ]
    fields = [
        'supplier',
        'entryDate',
        'amount',
    ]
    autocomplete_fields = ('supplier',)


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
