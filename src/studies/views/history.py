from django.shortcuts import render
from studies.models import Exam, Study

def exam_history(request):
    exams = Exam.objects.all().order_by('-created_at')
    return render(request, 'studies/exam_history.html', {'exams': exams})


def study_history(request):
    studies = Study.objects.all().order_by('-created_at')
    return render(request, 'studies/study_history.html', {'studies': studies})
