# api/views.py
from rest_framework import generics
from rest_framework.permissions import AllowAny
from pets.models import Pet
from medical_records.models import MedicalRecord
from .serializers import PetSerializer, MedicalRecordSerializer
from rest_framework.permissions import AllowAny

class PetPublicDetailView(generics.RetrieveAPIView):
    queryset = Pet.objects.all()
    serializer_class = PetSerializer
    permission_classes = [AllowAny] 
    lookup_field = 'qr_uuid'
    lookup_url_kwarg = 'uuid'

class MedicalRecordListCreateView(generics.ListCreateAPIView):
    """
    Защищённый API: список и создание записей (только для авторизованных).
    """
    serializer_class = MedicalRecordSerializer

    def get_queryset(self):
        return MedicalRecord.objects.filter(pet__owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)