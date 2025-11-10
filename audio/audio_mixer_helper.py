from pydub.effects import speedup
from pydub import AudioSegment


class AudioMixerHelper:
    @staticmethod
    def speed_up_audio(
        input_file_path: str,
        output_file_path: str,
        speed: float,
    ) -> None:
        """Speed up audio file using ffmpeg."""
        audio = AudioSegment.from_file(input_file_path)
        sped_up_audio: AudioSegment = speedup(audio, playback_speed=speed)
        sped_up_audio.export(output_file_path, format="mp3")
