import warnings
warnings.filterwarnings('ignore')
import awswrangler as wr
import time
from deepeval.test_case import LLMTestCase

if __name__ == "__main__":
    from metadata.patient_metadata import patient_dictionary
    from data_pipeline import DataPipeline
    from helper import Helper
    from prompts.prompt_generator import generate_summary_prompt
    from custom_llm import CustomLLM
    from validation import output_example
    from deepeval.metrics import GEval
    from deepeval.test_case import LLMTestCaseParams
    # ================================================================#
    # Read YAML file
    config_loaded = Helper.load_yaml_to_dict("config.yml")
    # ================================================================#
    for transcript_name, value in patient_dictionary.items():
        start_time = time.time()
        # ===============================================================#
        transcript = Helper.read_file(folder_path="transcripts",file_path=transcript_name)
        if config_loaded['zoomdata_usage']:
            zoomdata = DataPipeline.get_zoomdata(patient_external_id=value['patient_external_id'], zoom_meeting_id=value['zoom_meeting_id'])
            dictionary_records = zoomdata.to_dict('records')[0]
        if config_loaded['metadata_usage']:
            metadata = DataPipeline.get_metadata(patient_external_id=value['patient_external_id'])
            metadata_dictionary_records = metadata.to_dict('records')[0]
        #================================================================#
        prompt = generate_summary_prompt()
        # ================================================================#
        # Custom LLM class uses gpt
        custom_llm = CustomLLM(
            model="gpt-4o",
            temperature=0.30
        )
        response = custom_llm.generate(messages = [{"role": "system", "content": prompt}, {"role": "user", "content": transcript}])
        # ================================================================#
        #print('response: ', response)
        end_time = time.time()
        elapsed_time = end_time - start_time
        #print('elapsed time: ', elapsed_time)
        # ================================================================#
        # Set up the test case with input (transcript), actual output (GPT response), and expected output (correct summary)
        test_case = LLMTestCase(
            input=transcript,
            actual_output=response,
            expected_output=output_example
        )

        correctness_metric = GEval(
            name="Correctness",
            criteria="Determine whether the actual summary output is factually correct, and aligns with the transcript. Consider the topics discussed in the example, but do not take the example literally.",
            evaluation_steps=[
                "Verify that the summary comprehensively covers all critical points from the transcript, including:"
                "Individuals in attendance(e.g., therapist, patient, family member, if relevant)"
                "Developments since the last session, including weight changes."
                "Symptoms and observable behaviors."
                "Interventions used and the patient's response to them."
                "Clinician’s evaluation and analysis."
                "Follow-up plan and proposed next steps."
                "Ensure there are no omissions or critical details left out."
            ],
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT,
                               LLMTestCaseParams.EXPECTED_OUTPUT],
        )

        conciseness_metric = GEval(
            name="Conciseness and Objectivity",
            criteria="Evaluate whether the response maintains brevity without losing key information, and if it adheres to an objective tone throughout. Consider the style discussed in the example, but do not take the example literally.",
            evaluation_steps=[
                "Ensure the response is succinct, using the least number of words necessary to convey all critical information accurately.",
                "Verify that the response adheres to the specified word count or length constraints, if applicable. If no word count is specified, ensure that the response is efficient and avoids unnecessary elaboration or excessive detail.",
                "Check for clarity and precision in language, avoiding redundancies and overly complex phrasing.",
                "Ensure that the tone is objective, without emotional bias, judgment, or subjective interpretation. The language should remain neutral and factual.",
                "Ensure that all critical elements from the transcript or input are addressed in a manner that avoids extraneous commentary or speculative language.",
                "Make sure that any conclusions, if provided, are supported by facts and are stated without personal opinions or subjective assumptions."
            ],
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT,
                               LLMTestCaseParams.EXPECTED_OUTPUT],
        )
        # Evaluate correctness of the response
        correctness_metric.measure(test_case)
        print(f"Correctness Score: {correctness_metric.score}")
        print(f"Reason: {correctness_metric.reason}")

        # Evaluate conciseness of the response
        conciseness_metric.measure(test_case)
        # Output the results of the evaluation
        print(f"Conciseness Score: {conciseness_metric.score}")
        print(f"Reason: {conciseness_metric.reason}")
        # ================================================================#

        if config_loaded['dev'] and config_loaded['metadata_usage'] and config_loaded['zoomdata_usage']:
            summ_df = DataPipeline.post_process(dictionary_records, response, prompt, correctness_metric, conciseness_metric, transcript_name,elapsed_time)
            wr.s3.to_parquet(
                df=summ_df,
                path=config_loaded['bucket']['transcript_output'],
                filename_prefix=f"{summ_df.iloc[0]['zoom_meeting_id'].astype(str)}",
                dataset=True,
                mode="append"
            )
            wr.s3.upload(local_file='./test_multiple_transcripts/'+transcript_name,
                         path=config_loaded['bucket']['transcripts']+'/'+transcript_name)
            print("Success")