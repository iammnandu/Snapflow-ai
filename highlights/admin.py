from django.contrib import admin
from .models import BestShot, DuplicateGroup, DuplicatePhoto

class BestShotAdmin(admin.ModelAdmin):
    list_display = ('event', 'category', 'score', 'created_at')
    list_filter = ('category', 'event')
    search_fields = ('event__title',)
    raw_id_fields = ('event', 'photo')

class DuplicatePhotoInline(admin.TabularInline):
    model = DuplicatePhoto
    extra = 0
    raw_id_fields = ('photo',)

class DuplicateGroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'event', 'similarity_threshold', 'photo_count', 'created_at')
    list_filter = ('event', 'similarity_threshold')
    search_fields = ('event__title',)
    inlines = [DuplicatePhotoInline]
    
    def photo_count(self, obj):
        return obj.photos.count()
    photo_count.short_description = 'Number of Photos'

admin.site.register(BestShot, BestShotAdmin)
admin.site.register(DuplicateGroup, DuplicateGroupAdmin)