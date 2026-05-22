from django.contrib import admin

from .models import ImageAuthorization, Profile, ReviewState, StudyPhrase, VanRegistration


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'whatsapp', 'user']
    search_fields = ['full_name', 'whatsapp', 'user__username', 'user__email']


@admin.register(StudyPhrase)
class StudyPhraseAdmin(admin.ModelAdmin):
    list_display = ['deck_key', 'order', 'chapter', 'short_text']
    search_fields = ['deck_key', 'italian_text', 'portuguese_text', 'chapter']
    list_filter = ['source_title', 'chapter']

    def short_text(self, obj):
        return obj.italian_text[:90]


@admin.register(ReviewState)
class ReviewStateAdmin(admin.ModelAdmin):
    list_display = ['user', 'phrase', 'due_at', 'interval_days', 'ease_factor', 'repetitions', 'lapses']
    list_filter = ['last_grade', 'due_at']
    search_fields = ['user__username', 'phrase__italian_text']


@admin.register(VanRegistration)
class VanRegistrationAdmin(admin.ModelAdmin):
    list_display = ['minor_name', 'minor_cpf', 'responsible_name', 'responsible_cpf', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['minor_name', 'minor_cpf', 'responsible_name', 'responsible_cpf', 'minor_document']
    readonly_fields = ['public_id', 'created_at', 'updated_at']


@admin.register(ImageAuthorization)
class ImageAuthorizationAdmin(admin.ModelAdmin):
    list_display = ['minor_name', 'minor_cpf', 'responsible_name', 'responsible_cpf', 'event_name', 'status', 'created_at']
    list_filter = ['status', 'event_start_date', 'created_at']
    search_fields = ['minor_name', 'minor_cpf', 'responsible_name', 'responsible_cpf', 'event_name']
    readonly_fields = ['public_id', 'created_at', 'updated_at']
