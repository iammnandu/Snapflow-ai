# save as extract_models.py in your Django project root
import os
import json
import django
from django.apps import apps

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SnapFlow.settings')
django.setup()

models_data = {}

for model in apps.get_models():
    model_name = model.__name__
    app_label = model._meta.app_label
    
    if app_label not in models_data:
        models_data[app_label] = {}
    
    models_data[app_label][model_name] = {
        'fields': [],
        'relations': []
    }
    
    # Get fields
    for field in model._meta.fields:
        field_data = {
            'name': field.name,
            'type': field.get_internal_type(),
            'null': field.null,
            'unique': field.unique,
        }
        models_data[app_label][model_name]['fields'].append(field_data)
    
    # Get relations
    for relation in model._meta.related_objects:
        related_data = {
            'from': model_name,
            'to': relation.related_model.__name__,
            'type': relation.get_internal_type() if hasattr(relation, 'get_internal_type') else 'RelatedModel',
            'name': relation.name,
        }
        models_data[app_label][model_name]['relations'].append(related_data)

# Save to JSON file
with open('django_models.json', 'w') as f:
    json.dump(models_data, f, indent=2)

print("Model information saved to django_models.json")