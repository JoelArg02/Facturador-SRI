from core.pos.models import Category
from core.security.form_handlers.base import BaseModelForm
from core.security.form_handlers.helpers import update_form_fields_attributes

class CategoryForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)

    class Meta:
        model = Category
        fields = '__all__'