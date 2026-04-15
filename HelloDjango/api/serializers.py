# api/serializers.py
from rest_framework import serializers
from pets.models import Pet
from medical_records.models import MedicalRecord

class PetSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField()
    qr_url = serializers.CharField()#(source='', read_only=True)

    class Meta:
        model = Pet
        fields = ['id', 'name', 'species', 'breed', 'birth_date', 'chip_number', 'owner', 'qr_url']

class MedicalRecordSerializer(serializers.ModelSerializer):
    pet = serializers.StringRelatedField()
    created_by = serializers.StringRelatedField()

    class Meta:
        model = MedicalRecord
        fields = ['id', 'pet', 'record_type', 'title', 'description', 'date', 'created_by', 'created_at']