from django.contrib import admin

from .models import Enrollment, EnrollmentEvent, Guardian, Student, StudentGuardian

admin.site.register(Student)
admin.site.register(Guardian)
admin.site.register(StudentGuardian)
admin.site.register(Enrollment)
admin.site.register(EnrollmentEvent)
