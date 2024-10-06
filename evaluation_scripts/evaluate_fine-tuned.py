import torch
from faster_whisper import WhisperModel
import numpy as np
import soundfile as sf
import os
import jiwer
from datasets import load_dataset
import pandas as pd
import re

dataset = load_dataset("jacktol/atc_dataset")

def generate_transcription_and_process_results(model_path, log_file_path="whisper-medium.en-fine-tuned-for-ATC-evalutation-data-raw.txt", seed=None):
    if seed is not None:
        np.random.seed(seed)

    model = WhisperModel(model_path, device="cuda" if torch.cuda.is_available() else "cpu", compute_type="float32")

    with open(log_file_path, "w") as log_file:
        wer_list = []

        for idx in range(len(dataset['test'])):
            sample = dataset['test'][idx]
            audio_array = np.array(sample['audio']['array'])
            audio_sr = sample['audio']['sampling_rate']
            ground_truth = sample['text']

            audio_path = f"temp_audio_{idx}.wav"
            sf.write(audio_path, audio_array, audio_sr)

            segments, _ = model.transcribe(audio_path, beam_size=5)
            prediction = ''.join([segment.text for segment in segments])

            normalized_prediction = prediction.strip()

            wer = jiwer.wer(ground_truth, normalized_prediction)
            wer_list.append(wer)

            log_file.write(f"--------------------------------------------------\n")
            log_file.write(f"Sample {idx + 1}:\n")
            log_file.write(f"Ground Truth: {ground_truth}\n")
            log_file.write(f"Prediction: {normalized_prediction}\n")
            log_file.write(f"Word Error Rate (WER): {wer * 100:.2f}%\n")
            log_file.write(f"--------------------------------------------------\n")

            if os.path.exists(audio_path):
                os.remove(audio_path)

        avg_wer = np.mean(wer_list) * 100

        log_file.write(f"\nAverage Word Error Rate (WER) across {len(dataset['test'])} samples: {avg_wer:.2f}%\n")
        log_file.write(f"--------------------------------------------------\n")

    process_evaluation_log(log_file_path, avg_wer)

def process_evaluation_log(log_file_path, avg_wer):
    with open(log_file_path, 'r') as file:
        data = file.read()

    pattern = r"Sample\s+(\d+):\s*Ground Truth:\s*(.+)\s*Prediction:\s*(.+)\s*Word Error Rate \(WER\):\s*([\d.]+)%"

    matches = re.findall(pattern, data)

    df = pd.DataFrame(matches, columns=['Sample', 'Ground Truth', 'Prediction', 'WER'])

    df['Sample'] = df['Sample'].astype(int)
    df['WER'] = df['WER'].astype(float)

    df_sorted = df.sort_values(by='WER', ascending=False)

    wer_str = f"{avg_wer:.2f}"

    csv_filename = f'whisper-medium.en-fine-tuned-for-ATC-{wer_str}-WER-evaluation-data_test.csv'
    df_sorted.to_csv(csv_filename, index=False)

    print(f"Average WER: {wer_str}%")
    print(f"Results saved to: {csv_filename}")

    if os.path.exists(log_file_path):
        os.remove(log_file_path)

if __name__ == "__main__":
    model_path = "jacktol/whisper-medium.en-fine-tuned-for-ATC-faster-whisper"
    generate_transcription_and_process_results(model_path=model_path)