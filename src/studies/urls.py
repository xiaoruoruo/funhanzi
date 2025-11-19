from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', RedirectView.as_view(url='exams/', permanent=True), name='home'),
    path('progress/', views.progress_view, name='progress'),
    
    # History URLs
    path('exams/', views.exam_history, name='exam_history'),
    path('studies/', views.study_history, name='study_history'),
    
    # Stats URL
    path('stats/', views.stats_view, name='show_stats'),
    
    # Study generation URLs
    path('study/chars/', views.generate_study_chars, name='generate_study_chars'),
    path('study/failed/', views.generate_failed_study, name='generate_failed_study'),
    path('study/review/', views.generate_review_study, name='generate_review_study'),
    path('study/cloze/', views.generate_cloze_test, name='generate_cloze_test'),
    path('study/words/', views.generate_find_words_puzzle, name='generate_find_words_puzzle'),
    path('study/ch_en_matching/', views.generate_ch_en_matching_study, name='generate_ch_en_matching_study'),
    
    # Exam generation URLs
    path('exam/read/', views.generate_read_exam, name='generate_read_exam'),
    path('exam/write/', views.generate_write_exam, name='generate_write_exam'),
    path('exam/review/read/', views.generate_review_exam_read, name='generate_review_exam_read'),
    path('exam/review/write/', views.generate_review_exam_write, name='generate_review_exam_write'),
    
    # Exam recording URL
    path('exam/record/<int:exam_id>/', views.record_exam, name='record_exam'),
    
    # Study completion URL
    path('study/done/<int:study_id>/', views.mark_study_done, name='mark_study_done'),
    
    # Study and exam viewing URLs
    path('study/view/<int:study_id>/', views.view_study, name='view_study'),
    path('exam/view/<int:exam_id>/', views.view_exam, name='view_exam'),

    # Lesson management URLs
    path('lessons/', views.lesson_list, name='lesson_list'),
    path('lessons/toggle/<int:lesson_num>/', views.toggle_lesson_learned, name='toggle_lesson_learned'),
]