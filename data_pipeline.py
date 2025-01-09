import awswrangler as wr
import pandas as pd
class DataPipeline():
    def __init__(self):
        return self
    @staticmethod
    def get_zoomdata(patient_external_id: str, zoom_meeting_id: int):
        """
        """
        input_data_query = f'''
        SELECT
        patient_external_id, zoom_meeting_id, duration, provider_full_name, patient_full_name, patient_week_at_appt_time, note_external_id, note_content
        FROM (
        SELECT
        zr.*,
        appts.appt_status as appt_status2,
        p.mrn
        FROM
        secure_equip_dw_staging.zoom_recordings as zr
        left join equip_dw.patients as p on p.patient_external_id = zr.patient_external_id
        left join equip_dw.appointments appts ON zr.zoom_meeting_id = appts.zoom_meeting_id)
        WHERE appt_status2 = 'FULFILLED' and provider_type = 'Therapist' and appt_type_name = 'Therapy 50-minute Session' 
        and note_content is not null and patient_external_id = '{patient_external_id}' and zoom_meeting_id = {zoom_meeting_id}
        '''
        query_exec_id = wr.athena.start_query_execution(sql=input_data_query)
        df = wr.athena.get_query_results(query_execution_id=query_exec_id)
        return df

    @staticmethod
    def get_metadata(patient_external_id):
        """
        """
        input_data_query = f'''
        with patient_info as (
            select 
            pte.patient_external_id,
            pte.patient_first_name,
            pte.patient_last_name,
            mp.chosen_name as patient_chosen_name,
            case 
                when pec.treatment_modality_derived = 'FBT' and pte.primary_diagnosis like 'Avoidant%' then 'fbt-arfid'
                when pec.treatment_modality_derived = 'FBT' then 'fbt'
                when pec.treatment_modality_derived = 'CBT' and pte.primary_diagnosis like 'Avoidant%' then 'cbt-arfid'
                when pec.treatment_modality_derived = 'CBT' then 'cbt-e' else null end modality,
            pte.primary_diagnosis,
            pte.age_at_admission
            from equip_dw.patient_treatment_episodes pte 
            left join equip_dw.patient_episode_cohorts pec 
            on pte.treatment_episode_id = pec.treatment_episode_id
            left join equip_dw.maud_patients mp 
            on pte.patient_external_id = mp.patient_external_id
        ),
        intake_survey as (
            select 
            patient_external_id,
            ed_diagnoses,
            ed_diagnoses_comment,
            primary_ed_symptoms,
            psychiatric_symptoms,
            primary_medical_conditions,
            primary_medical_conditions_comment,
            prior_ed_treatment,
            psychiatric_diagnoses,
            suicidal_ideations,
            past_trauma,
            trauma_description,
            family_or_friend_suicide,
            living_situation,
            sdoh_food_insecurity_text,
            primary_symptoms,
            primary_symptoms_comment,
            surgeries,
            surgeries_comment,
            hospitalized_flag,
            hospitalization_reason,
            intake_weight,
            intake_weight_six_months_ago,
            caloric_intake,
            current_medication_names
            from equip_dw.maud_intake_surveys
        ),
        presenting_problem_note as (
            select 
            patient_external_id,
            note_external_id,
            description as presenting_problem_text
            from equip_dw.clinical_notes where title = 'Presenting Problem'
        )
        select 
        pi.patient_external_id,
        pi.patient_first_name,
        pi.patient_last_name,
        pi.patient_chosen_name,
        pi.modality,
        coalesce(pi.primary_diagnosis,array_join(i.ed_diagnoses,';'), i.ed_diagnoses_comment) as primary_diagnosis,
        pi.age_at_admission,
        i.primary_ed_symptoms,
        i.psychiatric_symptoms,
        i.psychiatric_diagnoses,
        i.primary_medical_conditions,
        i.primary_medical_conditions_comment,
        i.prior_ed_treatment,
        i.suicidal_ideations,
        i.past_trauma,
        i.trauma_description,
        i.family_or_friend_suicide,
        i.living_situation,
        i.sdoh_food_insecurity_text as sdoh_food_insecurity,
        i.primary_symptoms,
        i.primary_symptoms_comment,
        i.hospitalized_flag,
        i.hospitalization_reason,
        i.intake_weight,
        i.intake_weight_six_months_ago,
        i.caloric_intake,
        i.current_medication_names,
        pp.presenting_problem_text
        from patient_info pi
        left join presenting_problem_note pp 
        on pi.patient_external_id = pp.patient_external_id
        left join intake_survey i 
        on pi.patient_external_id = i.patient_external_id
        where pi.patient_external_id = '{patient_external_id}'
        '''
        query_exec_id = wr.athena.start_query_execution(sql=input_data_query)
        df = wr.athena.get_query_results(query_execution_id=query_exec_id)
        return df
    @staticmethod
    def post_process(dictionary_records, summ, prompt, eval_correctness, eval_conciseness, transcript_name, elapsed_time):
        """
        Post-process the generated summary.

        Parameters:
        dictionary_records (dict): The dictionary of the meta data.
        summ (str): The summary generated by the LLM.
        prompt (str): The prompt used to generate the summary.
        eval (list): The evaluation scores and reasons.
        transcript_name (str): The name of the transcript file.
        elapsed_time (float): The time taken to generate the summary.

        Returns:
        df: pandas dataframe.
        """
        df = pd.DataFrame({k: [v] for k, v in dictionary_records.items()})
        df['llm_note_summary'] =  summ
        df['prompt'] = prompt
        df['eval_correct_score'] = eval_correctness.score
        df['eval_correct_reason'] = eval_correctness.reason
        df['eval_concise_score'] = eval_conciseness.score
        df['eval_concise_reason'] = eval_conciseness.reason
        df['transcript_file_name'] = transcript_name
        df['time_summary'] = elapsed_time
        return(df)