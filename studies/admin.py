from django.contrib import admin

from .models import Profile, ReviewState, StudyPhrase


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'whatsapp', 'user']
    search_fields = ['full_name', 'whatsapp', 'user__username', 'user__email']


@admin.register(StudyPhrase)
class StudyPhraseAdmin(admin.ModelAdmin):
    list_display = ['order', 'chapter', 'short_text']
    search_fields = ['italian_text', 'portuguese_text', 'chapter']
    list_filter = ['source_title', 'chapter']

    def short_text(self, obj):
        return obj.italian_text[:90]


@admin.register(ReviewState)
class ReviewStateAdmin(admin.ModelAdmin):
    list_display = ['user', 'phrase', 'due_at', 'interval_days', 'ease_factor', 'repetitions', 'lapses']
    list_filter = ['last_grade', 'due_at']
    search_fields = ['user__username', 'phrase__italian_text']
