from flask import render_template, redirect, url_for, flash, request, abort, \
    current_app, jsonify, make_response
from flask_login import current_user, login_required
from flask.ext import excel
from sqlalchemy import func, distinct, select, and_
from . import main
from .forms import EditProfileForm, EditProfileAdminForm, PostForm
from .. import db
from ..models import (Permission, Role, User, Geo, UserType, Mapping, LocationTargets, Exam, Village, Ward,
    Location, Education, EducationLevel, Referral, Parish, SubCounty, Recruitments, Registration, Interview,
    Branch, Cohort, RecruitmentUsers, LinkFacility, CommunityUnit)
from ..decorators import admin_required, permission_required
from flask_googlemaps import Map, icons
from datetime import date, datetime
import time
import csv, os, time, calendar
from ..data import data
import io
import csv
import random

currency = 'UGX '

# @main.route('/main', methods=['GET', 'POST'])
# def index_main():
#     if current_user.is_anonymous():
#         return redirect(url_for('auth.login'))
#     else:
#         return jsonify(id=current_user.id)


@main.route('/', methods=['GET', 'POST'])
@login_required
def index():
    page = {'title': 'Home'}
    total_registrations = Registration.query.filter_by(archived=0)
    registrations = total_registrations.count()

    total_mappings = Mapping.query.filter_by(archived=0)
    mappings = total_mappings.count()

    total_recruitments = Recruitments.query.filter_by(archived=0)
    recruitments = total_recruitments.count()

    recruitment = Recruitments.query.filter_by(archived=0).limit(5).all()

    villages = Village.query.filter_by(archived=0)
    if current_user.is_anonymous():
        # return redirect(url_for('auth.login'))

        return render_template('index.html', page=page, registrations=registrations, mappings=total_mappings,
                               recruitments=recruitments, villages=villages, currency=currency)
    else:
        return render_template('index.html', page=page, registrations=registrations, mappings=total_mappings,
                               recruitments=recruitments, villages=villages, currency=currency,
                               recruitment=recruitment)


@main.route('/registration/<string:id>', methods=['GET', 'POST'])
@login_required
def application_details(id):
    if request.method == 'GET':
        a = Registration.query.filter_by(id=id).first_or_404()
        mytime = time.strftime('%Y-%m-%d', time.localtime(1347517370))
        dob = time.strftime('%Y-%m-%d', time.localtime(a.dob / 1000))
        birthdate = datetime.strptime(dob, '%Y-%m-%d')
        age = ((datetime.today() - birthdate).days/365)
        page = {'title':a.name, 'subtitle':'Registration details'}
        # age = time.time() - float(a.dob)
        qualified = a.dob
        interview = Interview.query.filter_by(applicant=id).first()
        exam = Exam.query.filter_by(applicant=id).first()
        return render_template('registration.html', exam=exam, dob=dob,
            page=page, interview=interview, registration=a, age=age)
    else:
        if request.form.get('action') == 'select':
            # add the application to the selected application
            # the selected application must be alist
            application = request.form.get('application_id')
            location = request.form.get('location_id')
            selected = SelectedApplication(application_id =application, location_id=location)
            db.session.add(selected)
            db.session.commit()
            return jsonify(status='ok')
    # fetch application details


@main.route('/selected-applications', methods=['GET', 'POST'])
@login_required
def selected_applications():
    if request.method == 'GET':
        applications = SelectedApplication.query.all()
        page = {'title': 'Selected Applications', 'subtitle':'Applications selected for interview'}
        return render_template('selected-applications.html', page=page, applications=applications, currency=currency)
    else:
        applications = request.form.getlist('applications[]')
        app = []
        if request.form.get('action') == 'select':
            for application_id in applications:
                application = SelectedApplication(
                    application_id = application_id
                )
                db.session.add(application)
                db.session.commit()
                app.append(application.id)
            return jsonify(app)
        else:
            return jsonify(status='no action selected')
        # return jsonify(details=request.form.getlist('applications[]'))@main.route('/selected-applications', methods=['GET', 'POST'])

@main.route('/trainings', methods=['GET', 'POST'])
@login_required
def selected_for_training():
  # the whole point here is to only show the applications that have been invited for training
  #  and for each application, show whether the person declined the interview or not
  # 
    if request.method == 'GET':
        applications = InterviewScore.query.filter_by(archived=0, invited_training=1)
        page = {'title': 'Training Selections', 'subtitle':'Applications selected for training'}
        return render_template('selected-for-training.html', page=page, applications=applications, currency=currency)
    else:
        applications = request.form.getlist('applications[]')
        app = []
        if request.form.get('action') == 'select':
            for application_id in applications:
                application = SelectedApplication(
                    application_id = application_id
                )
                db.session.add(application)
                db.session.commit()
                app.append(application.id)
            return jsonify(app)
        else:
            return jsonify(status='no action selected')
        # return jsonify(details=request.form.getlist('applications[]'))



@main.route('/training-list', methods=['GET', 'POST'])
@login_required
def training_list():
  # the whole point here is to only show the applications that have been invited for training
  #  and for each application, show whether the person declined the interview or not
  # 
    if request.method == 'GET':
        applications = InterviewScore.query.filter_by(archived=0, invited_training=1, confirmed_attendance=1)
        page = {'title': 'Training Selections', 'subtitle':'Applications selected for training'}
        return render_template('selected-for-training.html', page=page, applications=applications, currency=currency)
    else:
        applications = request.form.getlist('applications[]')
        app = []
        if request.form.get('action') == 'select':
            for application_id in applications:
                application = SelectedApplication(
                    application_id = application_id
                )
                db.session.add(application)
                db.session.commit()
                app.append(application.id)
            return jsonify(app)
        else:
            return jsonify(status='no action selected')
        # return jsonify(details=request.form.getlist('applications[]'))


@main.route('/export-scoring-tool/<string:id>', methods=['GET'])
@login_required
def export_scoring_tool(id):
    # get the registrations for the recruitment
    # Define our CSV
    dest = io.StringIO()
    writer = csv.writer(dest)
    data = []
    recruitment = Recruitments.query.filter_by(id=id).first_or_404()
    if recruitment.country == 'KE':
        header = [
            'CHEW Name',
            'CHEW Contact',
            'Candidate Name',
            'Candidate Mobile',
            'Gender',
            'Year of Birth',
            'Age',
            'Subcounty',
            'Ward',
            'Village/zone/cell',
            'Landmark',
            'CU (Community Unit)',
            'Link Facility',
            'No of Households',
            'Read/speak English',
            'Years at this Location',
            'Other Languages',
            'CHV',
            'GOK Training',
            'Other Trainings',
            'Highest education level',
            'Previous/Current health or business experience',
            'Community group membership',
            'Financial Accounts',
            'Recruitment Comments',
            'Math Score',
            'Reading Comprehension',
            'About you',
            'Total Score',
            'Eligible for Interview',
            'Interview: Overall Motivation',
            'Interview: Ability to work with communities',
            'Interview: Mentality',
            'Interview:Selling skills',
            'Interview: Interest in health',
            'Interview: Ability to invest',
            'Interview: Interpersonal skills',
            'Interview: Ability to commit',
            'Interview Score',
            'DO NOT ASK OUTLOUD: Any conditions to prevent joining?',
            'Tranport as Per Recruitment',
            'Comments',
            'Qualify for Training',
            'Completed By',
            'Invite for Training']
        data.append(header)
        registrations = Registration.query.filter(Registration.recruitment == id)
        for registration in registrations:
            # metadata for registration include:
            # Exam, Interview, Chew, Recruitment, Link Facility, subcounty, education, added, by, referral, ward
            # Get Exam
            
            exam = Exam.query.filter(Exam.applicant == registration.id).first()
            interview = Interview.query.filter(Interview.applicant == registration.id).first()
            if registration.referral is not None and registration.referral != '':
                chew = Referral.query.filter_by(id=registration.referral).first()
            else:
                chew = Referral.query.filter_by(id='0').first()
            link_facility = LinkFacility.query.filter_by(id=registration.link_facility).first()
            subcounty = SubCounty.query.filter_by(id=registration.subcounty).first()
            education = Education.query.filter_by(id=registration.education).first()
            ward = Ward.query.filter_by(id=registration.ward).first()
            community_unit = CommunityUnit.query.filter_by(id=registration.cu_name).first()
            
            math = 0
            english = 0
            personality = 0
            exam_total = 0
            exam_passed = "N"
            if exam:
                if exam.math == 0 or exam.english == 0 or exam.personality == 0:
                    exam_passed= "N"
                elif exam.total_score() < 10:
                    exam_passed = "N"
                else:
                    exam_passed = "Y"
                exam_total = exam.total_score()
                math = exam.math
                english = exam.english
                personality = exam.personality
                
            user = ""
            motivation = 0
            community = 0
            mentality = 0
            selling = 0
            health = 0
            investment = '0'
            interpersonal = '0'
            commitment = 0
            total_score = 0
            canjoin = "N"
            qualified = "N"
            comment = ""
            selected = ""
    
            if interview:
                user = str(interview.user.name)
                motivation = interview.motivation
                community = interview.community
                mentality = interview.mentality
                selling = interview.selling
                health = interview.health
                investment = str(interview.investment)
                interpersonal = str(interview.interpersonal)
                commitment = interview.commitment
                total_score = interview.total_score()
                qualified = 'Y' if interview.has_passed and exam_passed == 'Y' else 'N'
                if total_score > 24 and interview.canjoin == 1 and exam_passed == 'Y':
                    qualified = 'Y'
                else:
                    qualified ='N'
                canjoin = 'Y' if interview.canjoin == 1 else 'N'
                comment = interview.comment.replace(',', ';')
                selected = 'Y' if interview.selected == 1 else 'N'  # if selected of not
            # Now that we have what we need, we generate the CSV rows
            row = [
                chew.name if chew is not None else registration.chew_name,
                chew.phone if chew is not None else registration.chew_number,
                registration.name,
                registration.phone.replace(',', ':'),
                registration.gender,
                registration.date_of_birth(),
                registration.age(),
                subcounty.name if subcounty is not None else registration.subcounty,
                ward.name if ward is not None else registration.ward,
                registration.village.replace(',', ':'),
                registration.feature.replace(',', ':'),
                community_unit.name if community_unit is not None else registration.cu_name,
                link_facility.facility_name if link_facility is not None else registration.link_facility,
                str(registration.households),
                "Y" if registration.english == 1 else "N",
                registration.date_moved,
                registration.languages.replace(',', ';'),
                
                "Y" if registration.is_chv == 1 else "N",
                "Y" if registration.is_gok_trained == 1 else "N",
                registration.trainings.replace(',', ':'),
                education.name if education is not None else registration.education,
                registration.occupation,
                "Y" if registration.community_membership == 1 else "N",
                "Y" if registration.financial_accounts == 1 else "N",
                registration.comment.replace(',', ';'),
                math,
                english,
                personality,
                exam_total,
                exam_passed,
                str(motivation),
                str(community),
                str(mentality),
                str(selling),
                str(health),
                str(investment),
                str(interpersonal),
                str(commitment),
                str(total_score),
                str(canjoin),
                str(registration.recruitment_transport),
                str(comment),
                str(qualified),
                str(user),
                str(selected),
            ]
            data.append(row)
        
    else:
        registrations = Registration.query.filter(Registration.recruitment == id)
        header = [
            'Referral Name',
            'Referral Title',
            'Referral Mobile No',
            'VHT?',
            'Candidate Name',
            'Candidate Mobile',
            'Gender',
            'Age',
            'District',
            'Subcounty',
            'Parish',
            'Village/zone/cell',
            'Landmark',
            'Read/Speak English',
            'Other Languages',
            'Years at this location',
            'Ever worked with BRAC?',
            'If yes as BRAC CHP?',
            'Highest Educational',
            'Community group memberships',
            'Maths Score',
            'Reading comprehension',
            'About You',
            'Total Marks',
            'Eligible for Interview',
            'Interview Completed by,',
            'Interview: Overall Motivation',
            'Interview: Ability to work with communities',
            'Interview: Mentality',
            'Interview:Selling skills',
            'Interview: Interest in health',
            'Interview: Ability to invest',
            'Interview: Interpersonal skills',
            'Interview: Ability to commit',
            'Interview Score',
            'DO NOT ASK OUTLOUD: Any conditions to prevent joining?',
            'Comments',
            'Qualify for Training',
            'Invite for Training']
        data.append(header)
    
        for registration in registrations:
            # Get Exam
            exam = Exam.query.filter(Exam.applicant == registration.id).first()
            math = 0
            english = 0
            personality = 0
            exam_total = 0
            exam_passed = "N"
            if exam:
                math = exam.math
                english = exam.english
                personality = exam.personality
                exam_total = exam.total_score()
                exam_passed = "Y" if exam.has_passed() and registration.brac != 1 else "N"
    
            interview = Interview.query.filter(Interview.applicant == registration.id).first()
            user = ""
            motivation = 0
            community = 0
            mentality = 0
            selling = 0
            health = 0
            investment = '0'
            interpersonal = '0'
            commitment = 0
            total_score = 0
            canjoin = "N"
            qualified = "N"
            comment = ""
            canjoin = ""
            selected = ""
    
            if interview:
                user = str(interview.user.name)
                motivation = interview.motivation
                community = interview.community
                mentality = interview.mentality
                selling = interview.selling
                health = interview.health
                investment = str(interview.investment)
                interpersonal = str(interview.interpersonal)
                commitment = interview.commitment
                total_score = interview.total_score()
                qualified = 'Y' if interview.has_passed and exam_passed == 'Y' else 'N'
                canjoin = 'Y' if interview.canjoin == 1 else 'N'
                comment = interview.comment.replace(',', ';')
                canjoin = 'Y' if interview.canjoin == 1 else 'N'
                selected = 'Y' if interview.selected == 1 else 'N'  # if selected of not
            # interview= Interview.query.filter(Interview.archived != 1)
            # Now that we have what we need, we generate the CSV rows
            row = [
                registration.referral,
                registration.referral_title,
                registration.referral_number,
                "Y" if registration.vht == 1 else "N",
                registration.name,
                registration.phone.replace(',', ':'),
                registration.gender,
                registration.age(),
                registration.district,
                registration.subcounty,
                registration.parish,
                registration.village,
                registration.feature.replace(',', ':'),
                "Y" if registration.english == 1 else "N",
                registration.languages.replace(',', ';'),
                registration.date_moved,
                "Y" if registration.brac == 1 else "N",
                "Y" if registration.brac_chp == 1 else "N",
                registration.education,
                "Y" if registration.community_membership == 1 else "N",
                math,
                english,
                personality,
                exam_total,
                exam_passed,
                str(user),
                str(motivation),
                str(community),
                str(mentality),
                str(selling),
                str(health),
                str(investment),
                str(interpersonal),
                str(commitment),
                str(total_score),
                str(canjoin),
                str(comment),
                str(qualified),
                str(selected),
            ]
            data.append(row)
    output = excel.make_response_from_array(data, 'csv')
    output.headers["Content-Disposition"] = "attachment; filename=scoring-tool.csv"
    output.headers["Content-type"] = "text/csv"
    return output


@main.route('/interview-scores', methods=['POST'])
@login_required
def interview_score():
    selection = request.form.get('selection_id')
    selected = SelectedApplication.query.filter_by(application_id=selection).first()
    app = {}
    total = (int(request.form.get('motivation')) + int(request.form.get('community_work')) +
      int(request.form.get('mentality')) + int(request.form.get('selling')) +
      int(request.form.get('health')) + int(request.form.get('investment')) +
      int(request.form.get('interpersonal')) + int(request.form.get('commitment')))

    score = InterviewScore(
        selection_id = selected.id,
        recruitment_id = selected.application.recruitment_id,
        interview_id = request.form.get('interview_id'),
        motivation = request.form.get('motivation'),
        community_work = request.form.get('community_work'),
        mentality = request.form.get('mentality'),
        selling = request.form.get('selling'),
        health = request.form.get('health'),
        investment = request.form.get('investment'),
        interpersonal = request.form.get('interpersonal'),
        commitment = request.form.get('commitment'),
        interview_total_score = total,
        user_id = current_user.id,
        location_id = selected.application.location_id,
        application_id = selection, 
    )
    db.session.add(score)
    db.session.commit()
    return jsonify(selection=selection, rec=selected.application.recruitment_id)



@main.route('/interview-score/<int:id>', methods=['GET', 'POST'])
@login_required
def get_interview_score(id):
    if request.method == 'GET':
      selection = SelectedApplication.query.filter_by(id=id).first_or_404()
      application = selection.application
      page = {'title':' '.join([application.l_name, application.m_name, application.f_name]), 'subtitle':'Interview Score'}
      age = calculate_age(application.date_of_birth)
      qualified = appplication_status(application)
      # I this location, what is the target (number of CHPs) needed?
      target = LocationTargets.query.filter_by(location_id=application.location_id, recruitment_id=application.recruitment_id, archived=0).first()
      invited = InterviewScore.query.filter_by(location_id=application.location_id, invited_training=1)
      # target = LocationTargets.query.filter(location_id=selection.location_id, recruitment=application.recruitment_id, archived=0).first()
      selected = False
      taken_interview = False
      if selection:
        selected = True
        interview_score = InterviewScore.query.filter_by(selection_id=selection.id).first()
        taken_interview = True if interview_score else False
      phones = ApplicationPhone.query.filter_by(application_id=application.id)
      return render_template('interview-score.html', phones=phones, invited=invited,
        taken_interview=taken_interview, selected=selected, target = target, currency=currency,
        selected_application=selection, score=interview_score, interview_score=interview_score,
        qualified=qualified, age=age, page=page, application=application)
    else:
      items = {}
      if request.form.get('action') == 'select':
        interview_score = InterviewScore.query.filter_by(id=request.form.get('interview')).first()
        interview_score.invited_training = 1
        db.session.add(interview_score)
        db.session.commit()
      if request.form.get('action') == 'confirm':
        interview_score = InterviewScore.query.filter_by(id=request.form.get('interview')).first()
        interview_score.confirmed_attendance = 1
        db.session.add(interview_score)
        db.session.commit()
      return jsonify(status='ok', data=request.form)


@main.route('/recruitments', methods=['GET', 'POST'])
@login_required
def recruitments():
  if request.method == 'GET':
    page={'title':'Recruitments', 'subtitle':'Recruitments done so far'}
    recruitments = Recruitments.query.filter_by(archived=0)
    return render_template('recruitments.html', recruitments=recruitments, currency=currency, page=page)
  else:
    # check if there is an iD or if the ID is blank
    if 'id' in request.form:
        recruitment = Recruitments.query.filter_by(id=request.form.get('id')).first()
        recruitment.name=request.form.get('name')
        db.session.commit()
        return jsonify(status='updated', id=recruitment.id)
    else:
        recruitments = Recruitments(name=request.form.get('name'), added_by=current_user.id)
        db.session.add(recruitments)
        db.session.commit()
        return jsonify(status='created', id=recruitments.id)

@main.route('/recruitment/<string:id>', methods=['GET', 'POST'])
@login_required
def recruitment(id):
  if request.method == 'GET':
    recruitment = Recruitments.query.filter_by(archived=0, id=id).first_or_404()
    registrations = Registration.query.filter_by(recruitment=id)
    page={'title':recruitment.name.title(), 'subtitle':recruitment.name if recruitment else 'Recruitments'}
    return render_template('recruitment.html', recruitment=recruitment, 
        registrations=registrations, page=page)
  else:
    if 'id' in request.form:
        recruitment = Recruitments.query.filter_by(id=request.form.get('id')).first()
        recruitment.name=request.form.get('name')
        db.session.commit()
        return jsonify(status='updated', id=recruitment.id)
    else:
        recruitments = Recruitments(name=request.form.get('name'), added_by=current_user.id)
        db.session.add(recruitments)
        db.session.commit()

        # also add the recruitment
        recruitment = RecruitmentUsers(user_id=current_user.id, recruitment_id= recruitments.id)
        return jsonify(status='created', id=recruitments.id)

@main.route('/registrations', methods=['GET', 'POST'])
@login_required
def applications():
    if request.method == 'GET':
        page = {'title': 'applications', 'subtitle': 'manage applications and create new applications'}
        villages = Location.query.all()
        referrals = Referral.query.all()
        educations = Education.query.all()
        edu_level = EducationLevel.query.all()
        recruitments = Recruitments.query.filter_by(archived=0)
        applications = Application.query.all()
        return render_template('applications.html', recruitments=recruitments, 
          applications=applications, page=page, villages=villages, currency=currency,
          referrals= referrals, educations=educations, edu_level=edu_level)
    else:
        if request.form.get('action') == 'select':
            # add the application to the selected application
            # the selected application must be alist
            for application in request.form.get('applications'):
                saved_application = Application.query.filter_by(id=application.id)
                selected = SelectedApplication(application_id =application.id, location_id=saved_application.location_id)
                db.session.add_all([selected])
                db.session.commit()
            return jsonify(status='ok')
        else:
            # save the records
            about = int(request.form.get('about')) if request.form.get('about') != '' else 0
            eng = int(request.form.get('english')) if request.form.get('english') != '' else 0
            maths = int(request.form.get('maths')) if request.form.get('maths') != '' else 0
            total = about + eng + maths

            application = Application(
            f_name =  request.form.get('f_name').title() if request.form.get('f_name') != '' else None,
            m_name = request.form.get('m_name').title() if request.form.get('m_name') != '' else None,
            l_name = request.form.get('l_name').title() if request.form.get('l_name') != '' else None,
            maths = request.form.get('maths') if request.form.get('maths') != '' else None,
            english = request.form.get('english') if request.form.get('english') != '' else None,
            about_you = request.form.get('about') if request.form.get('about') != '' else None,
            total_score = total,
            gender = request.form.get('gender').title() if request.form.get('gender') != '' else None,
            date_of_birth = request.form.get('date_of_birth').title() if request.form.get('date_of_birth') != '' else None,
            location_id = request.form.get('village_id').title() if request.form.get('village_id') != '' else None,
            landmark = request.form.get('landmark').title() if request.form.get('landmark') != '' else None,
            date_moved = request.form.get('date_moved').title() if request.form.get('date_moved') != '' else None,
            referral_id = request.form.get('referral_id').title() if request.form.get('referral_id') != '' else None,
            education_id = request.form.get('education_id').title() if request.form.get('education_id') != '' else None,
            edu_level_id = request.form.get('edu_level_id').title() if request.form.get('edu_level_id') != '' else None,
            vht = request.form.get('vht').title() if request.form.get('vht') != '' else None,
            languages = request.form.get('languages').title() if request.form.get('languages') != '' else None,
            worked_brac = request.form.get('worked_brac').title() if request.form.get('worked_brac') != '' else None,
            brac_chp = request.form.get('brac_chp').title() if request.form.get('brac_chp') != '' else None,
            community_membership = request.form.get('community_membership').title() if request.form.get('community_membership') != '' else None,
            read_english = request.form.get('read_english').title() if request.form.get('read_english') != '' else None,
            recruitment_id = request.form.get('recruitment') if request.form.get('recruitment') != '' else None
            )
            db.session.add(application)
            db.session.commit()
            phones = request.form.getlist('phone[]')
            for phone in phones:
                pid = ApplicationPhone(
                    application_id = application.id,
                    phone = phone
                )
                db.session.add(pid)
                db.session.commit()
            return jsonify(status='ok', ref=request.form.get('recruitment') if request.form.get('recruitment') != '' else None,)

@main.route('/country', methods=['GET', 'POST'])
@main.route('/region', methods=['GET', 'POST'])
@main.route('/county', methods=['GET', 'POST'])
@main.route('/district', methods=['GET', 'POST'])
@main.route('/sub-county', methods=['GET', 'POST'])
@main.route('/parish', methods=['GET', 'POST'])
@main.route('/ward', methods=['GET', 'POST'])
@main.route('/locations', methods=['GET', 'POST'])
@login_required
def create_location():
    # if request.method == 'POST':
    if request.method == 'POST':
        parent = request.form.get('parent')  if request.form.get('parent') != '0' else None
        location = Location(
            name = request.form.get('name').title(),
            parent = parent,
            lat = request.form.get('lat'),
            lon = request.form.get('lon'),
            admin_name = request.form.get('admin_name').title()
        )
        db.session.add(location)
        db.session.commit()
        return jsonify(status='ok', parent=parent)
    else:
        param = request.path.strip('/')
        all_locations = Location.query.all()
        if param is None or param == 'locations':
            locations = Location.query.all()
        else:
            locations = Location.query.filter_by(admin_name=param.title())
        page = {'title': param, 'subtitle': 'mapped '+param}
        inputmap = Map(
            identifier="view-side",
            lat=-1.2728,
            lng=36.7901,
            zoom=8,
            markers=[(-1.2728, 36.7901)]
        )
        return render_template('location.html', page=page, map=inputmap, currency=currency,
         all_locations=all_locations,  locations=locations)


@main.route('/villages', methods=['GET', 'POST'])
@login_required
def create_village():
    # if request.method == 'POST':
    if request.method == 'POST':
        pass
    else:
        page = {'title': 'Villages', 'subtitle': 'mapped Villages'}
        villages = Village.query.filter_by(archived=0)
        inputmap = Map(
            identifier="view-side",
            lat=-1.2728,
            lng=36.7901,
            zoom=8,
            markers=[(-1.2728, 36.7901)]
        )
        return render_template('villages.html', page=page, map=inputmap, currency=currency,
         villages=villages)


@main.route('/mappings', methods=['GET', 'POST'])
@login_required
def create_mappings():
    # if request.method == 'POST':
    if request.method == 'POST':
        pass
    else:
        page = {'title': 'Mappings', 'subtitle': ' Mappings'}
        mappings = Mapping.query.all()
        inputmap = Map(
            identifier="view-side",
            lat=-1.2728,
            lng=36.7901,
            zoom=8,
            markers=[(-1.2728, 36.7901)]
        )
        return render_template('mappings.html', page=page, map=inputmap, currency=currency,
         mappings=mappings)
    
    
@main.route('/mapping/<string:id>', methods=['GET', 'POST'])
@login_required
def get_mapping_data(id):
    # if request.method == 'POST':
    if request.method == 'POST':
        pass
    else:
        page = {'title': 'Mappings', 'subtitle': ' Mappings'}
        color = ['dark', 'grey', 'blue', 'green', 'red']
        mapping = Mapping.query.filter_by(id=id).first()
        parishes = Parish.query.filter_by(mapping_id=id)
        subcounties = SubCounty.query.filter_by(mappingId=id)
        villages = Village.query.filter_by(mapping_id=id)
        return render_template('mapping.html', page=page, villages=villages, mapping=mapping, parishes=parishes,
                               subcounties=subcounties, color=color)
    
    
@main.route('/branches', methods=['GET', 'POST'])
@login_required
def branches():
    if request.method == 'POST':
        branch = Branch(
            name = request.form.get('name').title(),
            location_id  = request.form.get('location_id'),
            lat = request.form.get('lat'),
            lon = request.form.get('lon')
        )
        db.session.add(branch)
        db.session.commit()
        return jsonify(status='ok', data=request.form)
    else:
        branches = Branch.query.all()
        branch_markers = []
        for record in branches:
            if record.lat != '' and record.lon != '':
                marker = {
                    'lat': record.lat,
                    'lng': record.lon,
                    'icon': icons.dots.blue,
                    'infobox': (
                        "<h2>"+record.name.title()+"</h2>"
                        "<br>200 New CHPs"
                        "<br><a href='village/"+str(record.id)+"'>More Details </a>"
                    )
                }
                branch_markers.append(marker)
        branch_maps = Map(
            identifier="branches",
            lat=-1.2728, # -1.272898, 36.790095
            lng=36.7901,
            zoom=8,
            style="height:500px;",
            markers=branch_markers,
            cluster = True,
            cluster_gridsize = 10
            )
        page = {'title': 'Branches', 'subtitle': 'List of branches'}
        
        locations = Location.query.all()
        return render_template('branches.html', branches=branches, currency=currency, clustermap=branch_maps, locations=locations, page=page)

@main.route('/cohort', methods=['GET', 'POST'])
@login_required
def cohort():
    if request.method == 'GET':
        page = {'title': 'Cohort', 'subtitle': 'List of all cohorts in all branches'}
        branches = Branch.query.all()
        cohorts = Cohort.query.all()
        return render_template('cohort.html', cohorts=cohorts, currency=currency, branches=branches, page=page)
    else:
        cohort = Cohort(
            cohort_number = request.form.get('name'),
            branch_id  = request.form.get('branch')
        )
        db.session.add(cohort)
        db.session.commit()
        return jsonify(status='ok', data=request.form)


@main.route('/get_location_expansion')
@login_required
def get_location_expansion():
  id = request.args.get('id')
  expansion = {}
  targets = LocationTargets.query.filter_by(location_id=id)
  for target in targets:
    expansion[time.mktime(date.datetime(target.recruitment.date_added))] = target.chps_needed
  return jsonify(expansion=expansion)



@main.route('/educations', methods=['GET', 'POST'])
@login_required
def educations():
    if request.method == 'GET':
        page = {'title': 'Education', 'subtitle': 'List of all education levels'}
        educations = Education.query.all()
        return render_template('educations.html', educations=educations, page=page, currency=currency)
    else:
        educations = Education(
            name = request.form.get('name')
        )
        db.session.add(educations)
        db.session.commit()
        return jsonify(status='ok', data=request.form)


@main.route('/education-level', methods=['GET', 'POST'])
@login_required
def education_levels():
    if request.method == 'GET':
        page = {'title': 'Education Level', 'subtitle': 'List of all education levels'}
        educations = Education.query.all()
        education_levels = EducationLevel.query.all()
        return render_template('education-level.html', education_levels=education_levels, educations=educations, page=page, currency=currency)
    else:
        educations = EducationLevel(
            level_name = request.form.get('name'),
            education_id = request.form.get('education')
        )
        db.session.add(educations)
        db.session.commit()
        return jsonify(status='ok', data=request.form)



@main.route('/refferals', methods=['GET', 'POST'])
@login_required
def refferals():
    if request.method == 'GET':
        page = {'title': 'Refferals', 'subtitle': 'List of persons who have reffered others'}
        refferals = Referral.query.all()
        locations = Location.query.all()
        return render_template('refferals.html', refferals=refferals, page=page, locations=locations, currency=currency)
    else:
        referral = Referral(
            name = request.form.get('name'),
            phone = request.form.get('phone'),
            title = request.form.get('title'),
            location_id = request.form.get('location')
        )
        db.session.add(referral)
        db.session.commit()
        return jsonify(status='ok', id=referral.id, data=request.form)

@main.route('/gmap-test')
def test_route():
    return render_template('gmap.html')

@main.route('/video-test')
def video_route():
    return render_template('video-bg.html')

@main.route('/user/<username>')
@login_required
def user(username):
    user = User.query.outerjoin(Geo).outerjoin(UserType)\
        .with_entities(User, Geo, UserType)\
        .filter(User.username==username).first_or_404()

    return render_template('user.html', user=user, vc_firms=[],
                           ai_firms=[], su_firms=[])


@main.route('/users/<username>')
@login_required
def users(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.', 'error')
        return redirect(url_for('main.index'))

    # get request arguments
    followed = request.args.get('followed', 1, type=int)

    # query for users
    if followed:
        results = user.followed.order_by(Follow.timestamp.desc()).all()
        users = [{'user': item.followed, 'timestamp': item.timestamp}
                 for item in results]
    else:
        results = User.query.order_by(User.username.asc()).all()
        users = [{'user': item, 'timestamp': None}
                 for item in results]
    

    return render_template('user_list.html', user=user, users=users,
                           followed=followed)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        # change values based on form input
        geo = Geo.query.filter_by(id=form.geo.data).first()
        current_user.name = form.name.data
        current_user.location = geo.geo_code
        current_user.about_me = form.about_me.data
        current_user.geo = Geo.query.get(form.geo.data)
        current_user.user_type = UserType.query.get(form.user_type.data)
        db.session.add(current_user)
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('main.user', username=current_user.username))
    # set inital values
    form.name.data = current_user.name
    # form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    form.geo.data = current_user.geo_id
    form.user_type.data = current_user.user_type_id
    return render_template('edit_profile.html', form=form)




@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        username = form.email.data.split('@')[0]
        geo = Geo.query.filter_by(id=form.geo.data).first()
        user.email = form.email.data
        user.username = username
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = geo.geo_code
        user.geo = Geo.query.get(form.geo.data)
        user.user_type = UserType.query.get(form.user_type.data)
        user.about_me = form.about_me.data
        if (form.edit_password.data):
            user.password = form.password.data
            user.app_name = form.password.data.encode('base64'),
        db.session.add(user)
        flash('The profile has been updated.', 'success')
        return redirect(url_for('main.user', username=user.username))
    form.email.data = user.email
    # form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    # form.location.data = user.location
    form.geo.data = user.geo_id
    form.user_type.data = user.user_type_id
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)


# @main.route('/post/<int:id>')
# @login_required
# def post(id):
#     post = Post.query.get_or_404(id)
#     return render_template('post.html', posts=[post])
#
#
# @main.route('/edit/<int:id>', methods=['GET', 'POST'])
# @login_required
# def edit(id):
#     post = Post.query.get_or_404(id)
#     if current_user != post.author and \
#             not current_user.can(Permission.ADMINISTER):
#         abort(403)
#     form = PostForm()
#     if form.validate_on_submit():
#         post.body = form.body.data
#         db.session.add(post)
#         flash('The post has been updated.', 'success')
#         return redirect(url_for('main.post', id=post.id))
#     form.body.data = post.body
#     return render_template('edit_post.html', form=form)


@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.', 'error')
        return redirect(url_for('main.index'))
    if current_user.is_following(user):
        flash('You are already following this user.', 'error')
        return redirect(url_for('main.user', username=username))
    current_user.follow(user)
    flash('You are now following %s.' % username, 'success')
    return redirect(url_for('main.user', username=username))


@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.', 'error')
        return redirect(url_for('main.index'))
    if not current_user.is_following(user):
        flash('You are not following this user.', 'error')
        return redirect(url_for('main.user', username=username))
    current_user.unfollow(user)
    flash('You are not following %s anymore.' % username, 'success')
    return redirect(url_for('main.user', username=username))


@main.route('/followers/<username>')
@login_required
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.', 'error')
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=current_app.config['FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followers of",
                           endpoint='main.followers', pagination=pagination,
                           follows=follows)

@main.route('/followed-by/<username>')
@login_required
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config['FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followed by",
                           endpoint='main.followed_by', pagination=pagination,
                           follows=follows)


@main.route('/company/<int:id>')
@login_required
def company(id):
    company = Company.query.join(User).filter(Company.id == id).first()
    if company is None:
        flash('Company Does Not Exist.', 'error')
        return redirect(url_for('main.index'))
    vc_firms = company.related_firms('vc')
    ai_firms = company.related_firms('ai')
    su_orgs = company.related_firms('su')
    return render_template('startup.html', company=company, vc_firms=vc_firms,
                           ai_firms=ai_firms, su_orgs=su_orgs)


@main.route('/companies/<username>')
@login_required
def companies(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.', 'error')
        return redirect(url_for('main.index'))

    # get request arguments
    filter_user = request.args.get('filter_user', 1, type=int)

    # query for companies
    query = Company.query
    if filter_user:
        query = query.filter(Company.user_id == user.id)
    query = query.order_by(Company.name.asc())

    # build response dataset
    company_list = query.all()
    companies = [{'id': item.id,
                  'name': item.name,
                  'owner': item.owner,
                  'city': item.city,
                  'state': item.state,
                  'country': item.country}
                 for item in company_list]
    return render_template('startup_list.html', user=user,
                           filter_user=filter_user, companies=companies)


@main.route('/firm/<int:id>')
@login_required
def firm(id):
    firm = Firm.query\
        .join(FirmType).join(FirmTier).join(User)\
        .filter(Firm.id == id).first()
    if firm is None:
        flash('Relationship Does Not Exist.', 'error')
        return redirect(url_for('main.index'))
    companies = firm.related_companies()
    return render_template('firm.html', firm=firm, companies=companies)

@main.route('/firms/<username>')
@login_required
def firms(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.', 'error')
        return redirect(url_for('main.index'))

    # get request arguments
    firm_type_code = request.args.get('firm_type_code', 'vc', type=str)
    filter_user = request.args.get('filter_user', 1, type=int)

    # format firm type
    firm_type = FirmType.query.filter_by(firm_type_code=firm_type_code).first()
    from inflect import engine
    p = engine()
    firm_type_full = firm_type.firm_type
    firm_type_code = firm_type.firm_type_code
    firm_type_p = p.plural(firm_type_full)

    # query for firms
    query = Firm.query\
        .join(FirmType, FirmType.id == Firm.firm_type_id)\
        .join(FirmTier, FirmTier.id == Firm.firm_tier_id)\
        .filter(FirmType.firm_type == firm_type_full)
    if filter_user:
        query = query.filter(Firm.user_id == user.id)
    query = query.order_by(FirmTier.firm_tier.asc(), Firm.name.asc())

    # build response dataset
    firm_list = query.all()
    firms = [{'id': item.id,
              'name': item.name,
              'type': item.type.firm_type,
              'tier': item.tier.firm_tier,
              'owner': item.owner,
              'city': item.city,
              'state': item.state,
              'country': item.country}
             for item in firm_list]
    return render_template('firm_list.html', user=user,
                           title=firm_type_p, type_code=firm_type_code,
                           filter_user=filter_user, endpoint='main.firms',
                           firms=firms)

@main.route('/csv')
def test_app():
  with open('data.csv', 'r') as f:
    data_numbers = {}
    districts = {}
    counties = {}
    sub_counties = {}
    for row in csv.reader(f.read().splitlines()):
      data_numbers[row[3]]= {'county':row[2], 'district':row[1], 'number':row[0]}
      if row[1] in districts:
        if row[2] in districts.get(row[1]):
          districts[row[1]][row[2]].append({'name':row[0], 'number':row[3]})
        else:
          districts[row[1]][row[2]] = []
          districts[row[1]][row[2]].append({'name':row[0], 'number':row[3]})
      else:
        districts[row[1]] = {}
        districts[row[1]][row[2]] = []
        districts[row[1]][row[2]].append({'name':row[0], 'number':row[3]})
  return jsonify(districts=districts)

def read_data(file):
  with open(data, 'r') as f:
    data = [row for row in csv.reader(f.read().splitlines())]
  return data

def appplication_status(app):
    status = True
    if calculate_age(app.date_of_birth) < 12 or calculate_age(app.date_of_birth) > 55:
        status = False
    if app.read_english == 0:
        status = False
    if calculate_age(app.date_moved) < 2:
        status = False
    if app.brac_chp == 1:
        status = False
    if app.maths == 0 or app.english == 0 or app.about_you == 0:
        status = False
    if (app.maths + app.english + app.about_you) < 30:
        status = False
    return status
def calculate_age(born):
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
def interview_pass(interview):
  status = False
  if interview.commitment >1 and interview.total_score > 24 and interview.special_condition == 'No':
    status = True
  return status
