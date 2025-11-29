from django.contrib import admin
from django import forms
from django.shortcuts import render
from django.http import HttpResponseRedirect
from .models import Lesson, Word, Study, Exam, StudyLog, ExamSettings, WordEntry, Book

class UpdateStudyDateForm(forms.Form):
    study_date = forms.DateField()

# Register your models here.

class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'order')
admin.site.register(Book, BookAdmin)


class LessonAdmin(admin.ModelAdmin):
    list_display = ('book', 'lesson_num', 'is_learned')
admin.site.register(Lesson, LessonAdmin)


class WordAdmin(admin.ModelAdmin):
    list_display = ('hanzi',)
admin.site.register(Word, WordAdmin)


class StudyAdmin(admin.ModelAdmin):
    list_display = ('type', 'created_at', 'done')
admin.site.register(Study, StudyAdmin)


class ExamAdmin(admin.ModelAdmin):
    list_display = ('type', 'created_at', 'recorded')
admin.site.register(Exam, ExamAdmin)


def update_study_date(modeladmin, request, queryset):
    if 'apply' in request.POST:
        form = UpdateStudyDateForm(request.POST)
        if form.is_valid():
            study_date = form.cleaned_data['study_date']
            queryset.update(study_date=study_date)
            modeladmin.message_user(request, f"Changed study date to {study_date.strftime('%Y-%m-%d')} for {queryset.count()} records.")
            return HttpResponseRedirect(request.get_full_path())
    else:
        form = UpdateStudyDateForm()

    return render(request, 'admin/update_study_date.html', {
        'title': 'Update Study Date',
        'queryset': queryset,
        'form': form
    })
update_study_date.short_description = "Update study date for selected logs"

class StudyLogAdmin(admin.ModelAdmin):
    list_display = ('word', 'type', 'score', 'study_date')
    actions = [update_study_date]
admin.site.register(StudyLog, StudyLogAdmin)


class ExamSettingsAdmin(admin.ModelAdmin):
    list_display = ('exam_type', 'num_chars', 'score_filter', 'days_filter', 'title', 'updated_at')
admin.site.register(ExamSettings, ExamSettingsAdmin)


class WordEntryAdmin(admin.ModelAdmin):
    list_display = ('word', 'score')
admin.site.register(WordEntry, WordEntryAdmin)

