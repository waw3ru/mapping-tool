import os
from . import api
from flask_login import login_required, current_user
from flask import Response, request, jsonify
import json
import time
from sqlalchemy import func, distinct, select, exists, and_
from .. import db
from ..models import (Permission, Role, User, IccmComponents, LinkFacility, Village, PartnerActivity, GpsData, Ward, County,
                      Location, Education, CommunityUnit, Referral, Recruitments, Interview, Exam, SubCounty,
                      Partner, Mapping, Parish, Training, Trainees, TrainingClasses, Cohort, Registration)
from .. data import data
import csv
import uuid


@api.route('/firm_summary')
@login_required
def firm_summary():
    summary = current_user.firm_summary()
    return Response(json.dumps(summary, indent=4), mimetype='application/json')

@api.route('/recruitments.json')
def recruitments_json():
  if request.method == 'GET':
    records = Recruitments.query.filter(Recruitments.archived != 1)
    return jsonify({'recruitments': [record.to_json() for record in records]})
  else:
    recruitments = Recruitments(name=request.form.get('name'))
    db.session.add(recruitments)
    db.session.commit()
    return jsonify(status='ok')


@api.route('/sync/ke-counties')
def get_ke_counties_json():
  if request.method == 'GET':
    records = County.query.all()
    return jsonify({'counties': [{'name':record.name, 'code':record.id,
                                  'subcounties':[subcounty.to_json() for subcounty in record.subcounties]}
                                 for record in records]})
  else:
    return jsonify(message='not permitted'), 200
    # return jsonify({"success": True}), 202


@api.route('/recruitment/<string:id>', methods=['GET', 'POST'])
def api_recruitment(id):
  if request.method == 'GET':
    page={'title':'Recruitments', 'subtitle':'Recruitments done so far'}
    recruitment = Recruitments.query.filter_by(id=id).first()
    return jsonify({'name':recruitment.name, 'id':recruitment.id})
  else:
    if request.form.get('action') =='confirmed' or request.form.get('action') =='draft':
      recruitment = Recruitments.query.filter_by(id=request.form.get('id')).first()
      recruitment.status = request.form.get('action')
      db.session.add(recruitment)
      db.session.commit()
      # also create a draft training, that needs to be confirmed by the Training Team.
      # When training has been confirmed, the person who confirmeed it becomes the owner
      if request.form.get('action') == 'confirmed':
        existing_training = Training.query.filter_by(recruitment_id=recruitment.id).first()
        if not existing_training:
          training = Training(
            id = uuid.uuid4(),
            training_name = recruitment.name,
            country = recruitment.country,
            district = recruitment.district,
            recruitment_id = recruitment.id,
            status = 1,
            client_time = time.time(),
            created_by = 1,
          )
          if recruitment.country == 'KE':
            if recruitment.subcounty_id is not None:
              training.subcounty_id = recruitment.subcounty_id
            if recruitment.county_id is not None:
              training.county_id = recruitment.county_id
          else:
            if recruitment.location_id is not None:
              training.location_id = recruitment.location_id
          db.session.add(training)
          db.session.commit()
      return jsonify(status='updated', id=recruitment.id)
    else:
      # recruitments = Recruitments(name=request.form.get('name'))
      # db.session.add(recruitments)
      # db.session.commit()
      return jsonify(status='ok')

@api.route('/users/json', methods=['GET'])
def api_users():
  users = User.query.all()
  api_data = []
  for user in users:
    api_data.append({'id':user.id, 'name':user.name, 'country':user.location, 'username': user.username, 'app_name': user.app_name, 'email': user.email})
  return jsonify(users=api_data)

@api.route('/test/json', methods=['GET', 'POST'])
def get_test_url():
  if request.method == 'GET':
    return jsonify(status='get')
  else:
    return jsonify(status='post')

@api.route('/sync/recruitments', methods=['GET', 'POST'])
def sync_recruitments():
  if request.method == 'GET':
    records  = Recruitments.query.order_by(Recruitments.client_time.asc()).filter(Recruitments.archived != 1)
    return jsonify({'recruitments':[record.to_json() for record in records]})
  else:
    status = []
    recruitment_list = request.json.get('recruitments')
    if recruitment_list is not None:
      for recruitment in recruitment_list:
        operation=''
        record = Recruitments.from_json(recruitment)
        saved_record  = Recruitments.query.filter(Recruitments.id == record.id).first()
        if saved_record:
          saved_record.id = recruitment.get('id')
          saved_record.name = recruitment.get('name')
          saved_record.lat = recruitment.get('lat')
          saved_record.lon = recruitment.get('lon')
          saved_record.subcounty = recruitment.get('subcounty')
          saved_record.district = recruitment.get('district')
          saved_record.country = recruitment.get('country')
          saved_record.county = recruitment.get('county')
          saved_record.division = recruitment.get('division')
          saved_record.added_by = recruitment.get('added_by')
          saved_record.comment = recruitment.get('comment')
          saved_record.client_time =recruitment.get('client_time')
          saved_record.synced = recruitment.get('synced')
          saved_record.archived = 0
          db.session.add(saved_record)
          db.session.commit()
          operation='updated'
        else:
          db.session.add(record)
          db.session.commit()
          operation='created'
        status.append({'id':record.id, 'status':'ok', 'operation': operation})
      return jsonify(status=status)
    else:
      return jsonify(error="No records posted")

@api.route('/sync/registrations', methods=['GET', 'POST'])
def sync_registrations():
  if request.method == 'GET':
    records  = Registration.query.filter(Registration.archived != 1)
    return jsonify({'registrations':[record.to_json() for record in records]})
  else:
    status = []
    registration_list = request.json.get('registrations')
    if registration_list is not None:
      for registration in registration_list:
        operation='' #to hold the operation performed so that we can inform the client
        record = Registration.from_json(registration)
        saved_record  = Registration.query.filter(Registration.id == record.id).first()
        if saved_record:
          saved_record.id=registration.get('id')
          saved_record.name =registration.get('name')
          saved_record.phone =registration.get('phone')
          saved_record.gender =registration.get('gender')
          saved_record.recruitment =registration.get('recruitment')
          saved_record.country =registration.get('country')
          saved_record.dob =registration.get('dob')
          saved_record.district =registration.get('district')
          saved_record.subcounty =registration.get('subcounty')
          saved_record.division =registration.get('division')
          saved_record.village =registration.get('village')
          saved_record.feature =registration.get('feature')
          saved_record.english =registration.get('english')
          saved_record.date_moved =registration.get('date_moved')
          saved_record.languages =registration.get('languages')
          saved_record.brac =registration.get('brac')
          saved_record.brac_chp =registration.get('brac_chp')
          saved_record.education =registration.get('education')
          saved_record.occupation =registration.get('occupation')
          saved_record.community_membership =registration.get('community_membership')
          saved_record.added_by =registration.get('added_by')
          saved_record.comment =registration.get('comment')
          saved_record.proceed =registration.get('proceed')
          saved_record.client_time =registration.get('client_time')
          saved_record.date_added =registration.get('date_added')
          saved_record.synced =registration.get('synced')
          saved_record.archived =registration.get('archived')
          saved_record.chew_name =registration.get('chew_name')
          saved_record.chew_number =registration.get('chew_number')
          saved_record.ward =registration.get('ward')
          saved_record.cu_name =registration.get('cu_name')
          saved_record.link_facility =registration.get('link_facility')
          saved_record.households =registration.get('households')
          saved_record.trainings =registration.get('trainings')
          saved_record.is_chv =registration.get('is_chv')
          saved_record.is_gok_trained =registration.get('is_gok_trained')
          saved_record.referral =registration.get('referral')
          saved_record.referral_number =registration.get('referral_number')
          saved_record.referral_title =registration.get('referral_title')
          saved_record.vht =registration.get('vht')
          saved_record.parish =registration.get('parish')
          saved_record.financial_accounts =registration.get('financial_accounts')
          saved_record.recruitment_transport =registration.get('recruitment_transport')
          saved_record.branch_transport =registration.get('branch_transport')
          db.session.add(saved_record)
          db.session.commit()
          operation='updated'
        else:
          db.session.add(record)
          db.session.commit()
          operation='created'
        status.append({'id':record.id, 'status':'ok', 'operation':operation})
      return jsonify(status=status)
    else:
      return jsonify(error="No records posted")
    
@api.route('/sync/link_facilities', methods=['GET', 'POST'])
def sync_link_facilities():
  if request.method == 'GET':
    records = LinkFacility.query.filter(LinkFacility.archived != 1)
    return jsonify({'link_facilities': [record.to_json() for record in records]})
  else:
    status = []
    link_facilities_list = request.json.get('link_facilities')
    if link_facilities_list is not None:
      for link_facility in link_facilities_list:
        saved_record = LinkFacility.query.filter(LinkFacility.id == link_facility.get('id')).first()
        if saved_record:
          saved_record.client_time = link_facility.get('date_added')
          operation = 'updated'
        else:
          operation = 'created'
        db.session.add(saved_record)
        db.session.commit()
        status.append({'id': saved_record.id, 'status': 'ok', 'operation': operation})
      return jsonify(status=status)
    else:
      return jsonify(error="No records posted")

@api.route('/sync/mapping', methods=['GET', 'POST'])
def sync_mapping():
  if request.method == 'GET':
    records = Mapping.query.filter(Mapping.archived != 1)
    return jsonify({'mappings': [record.to_json() for record in records]})
  else:
    status = []
    mapping_list = request.json.get('mappings')
    if mapping_list is not None:
      for mapping in mapping_list:
        record = Mapping.from_json(mapping)
        saved_record = Mapping.query.filter(Mapping.id == record.id).first()
        if saved_record:
          operation = 'needs update'
        else:
          operation = 'created'
          db.session.add(record)
          db.session.commit()
          
        status.append({'id': record.id, 'status': 'ok', 'operation': operation})
      return jsonify(status=status)
    else:
      return jsonify(error=mapping_list)

@api.route('/sync/parish', methods=['GET', 'POST'])
def sync_parish():
  if request.method == 'GET':
    records = Parish.query.filter(Parish.archived != 1)
    return jsonify({'parish': [record.to_json() for record in records]})
  else:
    status = []
    parish_list = request.json.get('parishes')
    if parish_list is not None:
      for parish in parish_list:
        saved_record = Parish.query.filter(Parish.id == parish.get('id')).first()
        if saved_record:
          saved_record.client_time = parish.get('date_added')
          operation = 'updated'
        else:
          operation = 'created'
        db.session.add(saved_record)
        db.session.commit()
        status.append({'id': saved_record.id, 'status': 'ok', 'operation': operation})
      return jsonify(status=status)
    else:
      return jsonify(error="No records posted")

@api.route('/sync/villages', methods=['GET', 'POST'])
def sync_village():
  if request.method == 'GET':
    records = Village.query.filter(Village.archived != 1)
    return jsonify({'villages': [record.to_json() for record in records]})
  else:
    status = []
    village_list = request.json.get('villages')
    if village_list is not None:
      for village in village_list:
        saved_record = Village.query.filter(Village.id == village.get('id')).first()
        new_village = Village(
          id=village.get('id'),
          village_name =village.get('village_name '),
          mapping_id =village.get('mapping_id '),
          lat =village.get('lat '),
          lon =village.get('lon '),
          country =village.get('country '),
          district =village.get('district '),
          county =village.get('county '),
          sub_county_id =village.get('sub_county_id '),
          parish_id =village.get('parish_id '),
          community_unit_id =village.get('community_unit_id '),
          ward =village.get('ward '),
          link_facility_id =village.get('link_facility_id '),
          area_chief_name =village.get('area_chief_name '),
          area_chief_phone =village.get('area_chief_phone '),
          distancetobranch =village.get('distancetobranch '),
          transportcost =village.get('transportcost '),
          distancetomainroad =village.get('distancetomainroad '),
          noofhouseholds =village.get('noofhouseholds '),
          mohpoplationdensity =village.get('mohpoplationdensity '),
          estimatedpopulationdensity =village.get('estimatedpopulationdensity '),
          economic_status =village.get('economic_status '),
          distancetonearesthealthfacility =village.get('distancetonearesthealthfacility '),
          actlevels =village.get('actlevels '),
          actprice =village.get('actprice '),
          mrdtlevels =village.get('mrdtlevels '),
          mrdtprice =village.get('mrdtprice '),
          presenceofhostels =village.get('presenceofhostels '),
          presenceofestates =village.get('presenceofestates '),
          number_of_factories =village.get('number_of_factories '),
          presenceofdistibutors =village.get('presenceofdistibutors '),
          name_of_distibutors =village.get('name_of_distibutors '),
          tradermarket =village.get('tradermarket '),
          largesupermarket =village.get('largesupermarket '),
          ngosgivingfreedrugs =village.get('ngosgivingfreedrugs '),
          ngodoingiccm =village.get('ngodoingiccm '),
          ngodoingmhealth =village.get('ngodoingmhealth '),
          nameofngodoingiccm =village.get('nameofngodoingiccm '),
          nameofngodoingmhealth =village.get('nameofngodoingmhealth '),
          privatefacilityforact =village.get('privatefacilityforact '),
          privatefacilityformrdt =village.get('privatefacilityformrdt '),
          synced =village.get('synced '),
          chvs_trained =village.get('chvs_trained '),
          client_time =village.get('client_time '),
          date_added =village.get('date_added '),
          archived =village.get('archived '),
          addedby =village.get('addedby '),
          comment =village.get('comment '),
          brac_operating =village.get('brac_operating '),
          mtn_signal =village.get('mtn_signal '),
          safaricom_signal =village.get('safaricom_signal '),
          airtel_signal =village.get('airtel_signal '),
          orange_signal =village.get('orange_signal '),
          act_stock =village.get('act_stock '),
        )
        if saved_record:
          operation = 'updated'
        else:
          operation = 'created'
          village = Village(
            
          )
        db.session.add(new_village)
        db.session.commit()
        status.append({'id': saved_record.id, 'status': 'ok', 'operation': operation})
      return jsonify(status=status)
    else:
      return jsonify(error="No records posted")

@api.route('/sync/partners', methods=['GET', 'POST'])
def sync_partner():
  if request.method == 'GET':
    records = Partner.query.filter(Partner.archived != 1)
    return jsonify({'partners': [record.to_json() for record in records]})
  else:
    status = []
    partner_list = request.json.get('partners')
    if partner_list is not None:
      for partner in partner_list:
        saved_record = Partner.query.filter(Partner.id == partner.get('id')).first()
        if saved_record:
          saved_record.client_time = partner.get('date_added')
          operation = 'updated'
        else:
          operation = 'created'
        db.session.add(saved_record)
        db.session.commit()
        status.append({'id': saved_record.id, 'status': 'ok', 'operation': operation})
      return jsonify(status=status)
    else:
      return jsonify(error="No records posted")


@api.route('/sync/community_unit', methods=['GET', 'POST'])
def sync_cu():
  if request.method == 'GET':
    records = CommunityUnit.query.filter(CommunityUnit.archived != 1)
    return jsonify({'community_units': [record.to_json() for record in records]})
  else:
    status = []
    community_unit_list = request.json.get('community_unit')
    if community_unit_list is not None:
      for cu in community_unit_list:
        saved_record = CommunityUnit.query.filter(CommunityUnit.id == cu.get('id')).first()
        if saved_record:
          saved_record.client_time = cu.get('date_added')
          operation = 'updated'
        else:
          operation = 'created'
        db.session.add(saved_record)
        db.session.commit()
        status.append({'id': saved_record.id, 'status': 'ok', 'operation': operation})
      return jsonify(status=status)
    else:
      return jsonify(error="No records posted")


@api.route('/sync/partners/activity', methods=['GET', 'POST'])
def sync_partner_cu():
  if request.method == 'GET':
    records = PartnerActivity.query.filter(PartnerActivity.archived != 1)
    return jsonify({'partner_cu': [record.to_json() for record in records]})
  else:
    status = []
    partner_cu_list = request.json.get('partners_cu')
    if partner_cu_list is not None:
      for partner_cu in partner_cu_list:
        saved_record = PartnerActivity.query.filter(PartnerActivity.id == partner_cu.get('id')).first()
        if saved_record:
          saved_record.client_time = partner_cu.get('date_added')
          operation = 'updated'
        else:
          operation = 'created'
        db.session.add(saved_record)
        db.session.commit()
        status.append({'id': saved_record.id, 'status': 'ok', 'operation': operation})
      return jsonify(status=status)
    else:
      return jsonify(error="No records posted")


@api.route('/sync/interviews', methods=['GET', 'POST'])
def sync_interviews():
  if request.method == 'GET':
    records  = Interview.query.filter(Interview.archived != 1)
    return jsonify({'interviews':[record.to_json() for record in records]})
  else:
    status = []
    interview_list = request.json.get('interviews')
    if interview_list is not None:
      for interview in interview_list:
        record = Interview.from_json(interview)
        saved_record  = Interview.query.filter(Interview.id == record.id).first()
        if saved_record:
          interview['client_time'] = interview.get('date_added')
          interview.pop('date_added', None)
          saved_record = record
          db.session.commit()
          operation='updated'
        else:
          db.session.add(record)
          db.session.commit()
          operation='created'
        status.append({'id':record.id, 'status':'ok', 'operation':operation})
      return jsonify(status=status)
    else:
      return jsonify(error="No records posted")


@api.route('/sync/exams', methods=['GET', 'POST'])
def sync_exams():
  if request.method == 'GET':
    records  = Exam.query.filter(Exam.archived != 1)
    return jsonify({'exams':[record.to_json() for record in records]})
  else:
    status = []
    exam_list = request.json.get('exams')
    if exam_list is not None:
      for exam in exam_list:
        record = Exam.from_json(exam)
        saved_record  = Exam.query.filter(Exam.id == record.id).first()
        if saved_record:
          saved_record.id =exam.get('id')
          saved_record.applicant = exam.get('applicant')
          saved_record.recruitment = exam.get('recruitment')
          saved_record.country = exam.get('country')
          saved_record.math = exam.get('math')
          saved_record.personality = exam.get('personality')
          saved_record.english = exam.get('english')
          saved_record.added_by = exam.get('added_by')
          saved_record.comment = exam.get('comment')
          saved_record.client_time = exam.get('client_time')
          saved_record.archived = 0
          db.session.add(saved_record)
          db.session.commit()
          operation='updated'
        else:
          print 'Creating exam'
          db.session.add(record)
          db.session.commit()
          operation='created'
        status.append({'id':record.id, 'status':'ok', 'operation':operation})
      return jsonify(status=status)
    else:
      return jsonify(error="No records posted")


@api.route('/sync/locations', methods=['GET', 'POST'])
def sync_locations():
  if request.method == 'GET':
    locations = Location.query.filter(Location.archived == 0)
    return jsonify({'locations': [location.to_json() for location in locations]})


@api.route('/create/ke/counties')
def create_ke_counties():
  with open(os.path.dirname(os.path.abspath(data.__file__))+'/kenya_county.csv', 'r') as f:
    for row in csv.reader(f.read().splitlines()):
      county = County(id=row[0], name=row[1], archived=0)
      db.session.add(county)
      db.session.commit()
  return jsonify(status='ok')


@api.route('/sync/counties', methods=['GET', 'POST'])
def sync_counties():
  if request.method == 'GET':
    locations = Location.query.filter(Location.archived == 0)
    if request.args.get('country'):
      country = request.args.get('country')
      locations = Location.query.filter_by(archived=0, admin_name='County', country=country.upper())
      return jsonify({'locations': [location.to_json() for location in locations]})
    # country = request.args.get('country')
    locations = Location.query.filter_by(archived=0, admin_name='County')
    return jsonify({'locations': [location.to_json() for location in locations]})

@api.route('/sync/gpsdata', methods=['GET', 'POST'])
def sync_gps_data():
  if request.method == 'GET':
    records  = GpsData.query.all()
    return jsonify({'gps':[record.to_json() for record in records]})
  else:
    status = []
    gps_list = request.json.get('gps')
    if gps_list is not None:
      for gps in gps_list:
        record = GpsData.from_json(gps)
        saved_record  = GpsData.query.filter(GpsData.id == record.id).first()
        if saved_record:
          pass
        else:
          db.session.add(record)
          db.session.commit()
        status.append({'id':record.id, 'status':'ok', 'operation':'saved'})
      return jsonify(status=status)
    else:
      return jsonify(error="No records posted")

@api.route('/sync/chew_referral', methods=['GET', 'POST'])
def sync_chew_referral():
  if request.method == 'GET':
    records  = Referral.query.all()
    return jsonify({'referrals':[record.to_json() for record in records]})
  else:
    status = []
    referral_list = request.json.get('chew_referrals')
    if referral_list is not None:
      for referral in referral_list:
        record = Referral.from_json(referral)
        saved_record  = Referral.query.filter(Referral.id == record.id).first()
        if saved_record:
          # update the referral
          pass
        else:
          db.session.add(record)
          db.session.commit()
        status.append({'id':record.id, 'status':'ok', 'operation':'saved'})
      return jsonify(status=status)
    else:
      return jsonify(error="No records posted")

@api.route('/sync/iccm-components', methods=['GET', 'POST'])
def sync_iccm_components():
  if request.method == 'GET':
    iccms = IccmComponents.query.filter_by(archived=0)
    return jsonify({'components': [r.to_json() for r in iccms]})
  else:
    return jsonify(error="No records posted")


@api.route('/sync/ke-subcounties', methods=['GET', 'POST'])
def sync_ke_subcounties():
  ke_subcounties = data.get_ke_subcounties()
  return jsonify(subcounties=ke_subcounties)


@api.route('/sync/ke/wards', methods=['GET', 'POST'])
def sync_ke_wards():
  wards = Ward.query.filter_by(archived=0)
  return jsonify(wards=[ward.to_json() for ward in wards])


@api.route('/get/training-data', methods=['GET', 'POST'])
def get_training_data():
  """
    Returns Json Payload for the recruitments, and only the selected Applicants
  """
  if request.method == 'GET':
    interviews = Interview.query.filter_by(selected=1)
    trainings=[]
    recruitments={}
    for interview in interviews:
      if interview.recruitment not in recruitments:
        recruitments[interview.recruitment] = interview.base_recruitment.to_json()
        recruitments[interview.recruitment]['data']['count'] = interviews.count()
        recruitments[interview.recruitment]['data']['registrations'] = []
      recruitments[interview.recruitment]['data']['registrations'].append(interview.registration.to_json())
    return jsonify(draft_trainings=recruitments)
  else:
    return jsonify(message='not allowed'), 403


@api.route('/sync/trainings', methods=['GET', 'POST'])
def get_trainings():
  """
    Returns Json Payload for the training data
  """
  if request.method == 'GET':
    trainings = Training.query.filter_by(archived=0)
    return jsonify(trainings=[r.to_json() for r in trainings])
  else:
    return jsonify(message='not allowed'), 403


@api.route('/sync/training-classes', methods=['GET', 'POST'])
def sync_training_classes():
  """
  Syncs training classes at the cloud and in the mobile app
  """
  if request.method == 'GET':
    records = TrainingClasses.query.all()
    return jsonify({'training-classes': [record.to_json for record in records]})
  else:
    status = []
    training_classes = request.json.get('training_classes')
    if training_classes is not None:
      for training_class in training_classes:
        record = TrainingClasses.from_json(training_class)
        saved_record = TrainingClasses.query.filter(TrainingClasses.id == record.id).first()
        if saved_record:
          saved_record.id = training_class.get('id')
          saved_record.class_name = training_class.get('class_name')
          saved_record.created_by = training_class.get('created_by')
          saved_record.client_time = training_class.get('client_time')
          saved_record.date_created = training_class.get('date_created')
          db.session.add(record)
          db.session.commit()
          operation = 'updated'
        else:
          db.session.add(record)
          db.session.commit()
          operation = 'added'
        status.append({'id': record.id, 'status': 'ok', 'operation': operation})
      return jsonify(status=status)
    else:
      return jsonify(message='No records posted')


@api.route('/sync/trainees', methods=['GET', 'POST'])
def sync_trainees():
  """
  Syncs trainees to and from the cloud
  """
  if request.method == 'GET':
    records = Trainees.query.all()
    return jsonify({'trainees': [record.to_json for record in records]})
  else:
    status = []
    trainees = request.json.get('trainees')
    if trainees is not None:
      for trainee in trainees:
        record = Trainees.from_json(trainee)
        saved_record = Trainees.query.filter(Trainees.id == record.id).first()
        if saved_record:
          saved_record.id = trainee.get('id')
          saved_record.registration_id = trainee.get('registration_id')
          saved_record.class_id = trainee.get('class_id')
          saved_record.training_id = trainee.get('training_id')
          db.session.add(record)
          db.session.commit()
          operation = 'updated'
        else:
          db.session.add(record)
          db.session.commit()
          operation = 'added'
        status.append({'id': record.id, 'status': 'ok', 'operation': operation})
        return jsonify(status=status)
      else:
        return jsonify(message='No records posted')
