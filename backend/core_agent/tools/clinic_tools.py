from database import get_services, get_available_slots, create_appointment, get_appointments

def get_clinic_services_and_prices():
    """Returns a list of all services provided by the clinic with their prices."""
    return get_services()

def check_available_slots(doctor_name=None, date=None):
    """Checks available slots. Can be filtered by doctor_name and date."""
    return get_available_slots(doctor_name, date)

def book_appointment_request(patient_name, patient_phone, slot_id, notes=""):
    """Books an appointment for a patient given a specific slot ID."""
    return create_appointment(patient_name, patient_phone, slot_id, notes)

def lookup_patient_appointment(patient_phone):
    """Looks up appointments for a given patient phone number."""
    apps = get_appointments()
    return [a for a in apps if a['phone'] == patient_phone]
