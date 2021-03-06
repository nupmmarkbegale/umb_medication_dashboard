import datetime, json
from django.http import HttpResponse
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render
from django.core import serializers
from umb_dashboard.views import respond_with_json
from umb_dashboard.models import ChangeMedicationRequest, MedPromptResponse, \
  SentMessage
from medactive.models import SideEffectsSurveyResponse, \
  SymptomsSurveyResponse, ClinicianAlert, ClinicianProfile, Participant, \
  ParticipantAction, DoseChangeRequest, TabClick

LOGIN_URL = '/umb/medactive/login/?next=/umb/medactive'
RESEARCHER_LOGIN_URL = '/umb/medactive/cohort_summary/login/?next=/umb/medactive/cohort_summary'

def is_clinician(user):
  return user.is_superuser or user.groups.filter(name='MedActive Clinicians').exists()

def is_researcher(user):
  return user.groups.filter(name='MedActive Researchers').exists()

@user_passes_test(is_clinician, login_url=LOGIN_URL)
def index(request):
  __check_in_clinician(request.user)

  return render(request, 'medactive_index.html')

def __check_in_clinician(clinician):
  profile, created = ClinicianProfile.objects.get_or_create(clinician_id=clinician.id)
  if created == False:
    profile.save()

@user_passes_test(is_clinician, login_url=LOGIN_URL)
def participants(request):
  if request.user.is_superuser:
    return respond_with_json(Participant.objects.filter(clinician_id__isnull=False))
  else:
    return respond_with_json(Participant.objects.filter(clinician_id=request.user.id))

@user_passes_test(is_clinician, login_url=LOGIN_URL)
def side_effects_survey_responses(request, participant_id):
  responses = SideEffectsSurveyResponse.objects.all_for_participant(participant_id)
  return respond_with_json(responses)

@user_passes_test(is_clinician, login_url=LOGIN_URL)
def symptoms_survey_responses(request, participant_id):
  responses = SymptomsSurveyResponse.objects.all_for_participant(participant_id)
  return respond_with_json(responses)

@user_passes_test(is_clinician, login_url=LOGIN_URL)
def update_clinician_alert(request, participant_id, alert_id):
  for alert in serializers.deserialize("json", request.body):
    alert.save()
  return HttpResponse("{}", content_type="application/json")

@user_passes_test(is_clinician, login_url=LOGIN_URL)
def clinician_alerts(request, participant_id):
  alert_types = ["non_adherence", "side_effects", "symptoms"]
  participant = Participant.objects.get(participant_id=participant_id)
  alerts = []
  for alert_type in alert_types:
    alert = find_uncleared_alert(request.user.id, participant, alert_type)
    if alert != None:
      alerts.append(alert)
  return respond_with_json(alerts)

def find_uncleared_alert(clinician_id, participant, alert_type):
  alert_manager = ClinicianAlert.objects

  # find the most recent uncleared alert
  alerts = alert_manager.filter(participant_id=participant.id, type=alert_type, is_cleared=False).order_by('-created_at') or []
  if len(alerts) >= 1:
    alerts = [alerts[0]]

  # find the timestamp of the last cleared alert as a frame of reference
  last_cleared_alerts = alert_manager.filter(participant_id=participant.id, type=alert_type, is_cleared=True).order_by('-created_at')[:1]
  last_alert_timestamp = datetime.datetime.min
  if len(last_cleared_alerts) == 1:
    last_alert_timestamp = last_cleared_alerts[0].updated_at
  details, eventDateTime = pending_alert_details(last_alert_timestamp, participant, alert_type)
  if len(details) > 0:
    participant_requests_contact = any_contact_requests(last_alert_timestamp, participant, alert_type)
    alert = alert_manager.create(clinician_id=clinician_id, participant_id=participant.id, type=alert_type,
      problem_details=details, participant_requests_contact=participant_requests_contact, event_date_time=eventDateTime)
    alerts.append(alert)

  if len(alerts) >= 1 and latest_response_value_is_negative(participant, alert_type):
    return alerts[-1]
  return None

def latest_response_value_is_negative(participant, alert_type):
  if alert_type == "non_adherence":
    return MedPromptResponse.objects.latest_value_is_negative(participant.participant_id)
  elif alert_type == "side_effects":
    return SideEffectsSurveyResponse.objects.latest_value_is_negative(participant.participant_id)
  elif alert_type == "symptoms":
    return SymptomsSurveyResponse.objects.latest_value_is_negative(participant.participant_id)

# return the frequency for the alert
def pending_alert_details(last_alert_timestamp, participant, alert_type):
  if alert_type == "non_adherence":
    return pending_negative_med_prompt_responses(last_alert_timestamp, participant)
  elif alert_type == "side_effects":
    return pending_negative_side_effects_responses(last_alert_timestamp, participant)
  elif alert_type == "symptoms":
    return pending_negative_symptoms_responses(last_alert_timestamp, participant)

def pending_negative_med_prompt_responses(last_alert_timestamp, participant):
  responses = MedPromptResponse.objects.negative_responses(participant.participant_id, start_time=last_alert_timestamp)
  details = (r.doseTime for r in responses)

  return (filter(None, details), responses[-1].eventDateTime if len(responses) > 0 else None)

def pending_negative_side_effects_responses(last_alert_timestamp, participant):
  HIGH_FREQ = 'Always'
  responses = SideEffectsSurveyResponse.objects.negative_responses(participant.participant_id, last_alert_timestamp)
  details = []
  details.append(next(("index" for r in responses if r.weight_concern_distress == HIGH_FREQ), None))
  details.append(next(("sexual_problems" for r in responses if r.sexual_problems_distress == HIGH_FREQ), None))
  details.append(next(("insomnia" for r in responses if r.insomnia_distress == HIGH_FREQ), None))
  details.append(next(("restlessness" for r in responses if r.restlessness_distress == HIGH_FREQ), None))
  details.append(next(("low_energy" for r in responses if r.low_energy_distress == HIGH_FREQ), None))
  details.append(next(("not_like_self" for r in responses if r.not_like_self_distress == HIGH_FREQ), None))
  details.append(next(("excess_sedation" for r in responses if r.excess_sedation_distress == HIGH_FREQ), None))
  details.append(next(("poor_concentration" for r in responses if r.poor_concentration_distress == HIGH_FREQ), None))
  details.append(next(("trembling" for r in responses if r.trembling_distress == HIGH_FREQ), None))

  return (filter(None, details), responses[-1].eventDateTime if len(responses) > 0 else None)

def pending_negative_symptoms_responses(last_alert_timestamp, participant):
  HIGH_FREQ = 'Almost all of the time'
  responses = SymptomsSurveyResponse.objects.negative_responses(participant.participant_id, last_alert_timestamp)
  details = []
  details.append(next(("index" for r in responses if r.paranoia_frequency == HIGH_FREQ), None))
  details.append(next(("media_communication" for r in responses if r.media_communication_frequency == HIGH_FREQ), None))
  details.append(next(("thought_insertion" for r in responses if r.thought_insertion_frequency == HIGH_FREQ), None))
  details.append(next(("special_mission" for r in responses if r.special_mission_frequency == HIGH_FREQ), None))
  details.append(next(("thought_broadcasting" for r in responses if r.thought_broadcasting_frequency == HIGH_FREQ), None))
  details.append(next(("hallucinations" for r in responses if r.hallucinations_frequency == HIGH_FREQ), None))
  details.append(next(("confused_thinking" for r in responses if r.confused_thinking_frequency == HIGH_FREQ), None))
  details.append(next(("paranoia" for r in responses if r.paranoia_frequency == HIGH_FREQ), None))
  details.append(next(("thought_disorders" for r in responses if r.thought_disorders_frequency == HIGH_FREQ), None))

  return (filter(None, details), responses[-1].eventDateTime if len(responses) > 0 else None)

def any_contact_requests(last_alert_timestamp, participant, alert_type):
  messages = SentMessage.objects.all_in_context(participant.participant_id, alert_type, last_alert_timestamp)

  return len(messages) > 0

@user_passes_test(is_clinician, login_url=LOGIN_URL)
def latest_action(request, participant_id):
  return respond_with_json(ParticipantAction.objects.latest(participant_id))

@user_passes_test(is_clinician, login_url=LOGIN_URL)
def create_change_medication_request(request, participant_id):
  input = json.loads(request.body)
  change_request = ChangeMedicationRequest(participant_id, input['message'])
  change_request.save()
  status = { 'status': change_request.status }
  participant = Participant.objects.get(participant_id=participant_id)
  DoseChangeRequest.objects.create(clinician=request.user, participant=participant, message=input['message'])

  return HttpResponse(json.dumps(status), content_type="application/json")

@user_passes_test(is_researcher, login_url=RESEARCHER_LOGIN_URL)
def cohort_summary(request):
  participants = Participant.objects.filter(clinician_id__isnull=False)
  today = datetime.date.today()
  dates = [today - datetime.timedelta(days=x) for x in range(1, 8)]
  params = {
    'participants': participants,
    'dates': dates,
    'app_name': 'MedActive'
  }

  return render(request, 'cohort_summary.html', params)

@user_passes_test(is_clinician, login_url=LOGIN_URL)
def contact_research_staff(request):
  from django.core.mail import send_mail
  from django.conf import settings
  send_mail('Clinician requires assistance', 'A clinician requires assistance',
    settings.DEFAULT_FROM_EMAIL, settings.RESEARCH_STAFF_EMAILS, fail_silently=True)
  request.user.medactive_help_request.create()

  return HttpResponse(status=200)

@user_passes_test(is_clinician, login_url=LOGIN_URL)
def log_clinician_view(request, participant_id):
  participant = Participant.objects.get(participant_id=participant_id)
  participant.save()

  return HttpResponse(status=200)

@user_passes_test(is_clinician, login_url=LOGIN_URL)
def log_tab_click(request, participant_id):
  participant = Participant.objects.get(participant_id=participant_id)
  attributes = json.loads(request.body)
  TabClick.objects.create(clinician=request.user, participant=participant, name=attributes['name'])

  return HttpResponse(status=200)
