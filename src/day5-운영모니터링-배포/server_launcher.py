import os
import subprocess
import sys
import threading
import time


def print_logs(process, name):
    """서버 프로세스의 로그를 실시간으로 출력하는 함수"""
    # stderr를 사용하여 uvicorn의 로그를 읽습니다.
    for line in iter(process.stderr.readline, ""):
        print(f"[{name} LOG] {line.strip()}")


def launch_fastapi_app(app_module_name: str, port: int):
    """
    FastAPI 앱을 로컬에서 실행합니다.
    """
    print(f"🚀 {app_module_name} 서버를 로컬 포트 {port}에서 시작합니다...")

    # Step 1: 기존 프로세스 정리
    try:
        # pkill을 사용하여 특정 포트를 사용하는 uvicorn 프로세스를 종료합니다.
        subprocess.run(["pkill", "-f", f"uvicorn.*{app_module_name}.*--port {port}"], capture_output=True)
        print(f"   🧹 포트 {port}의 기존 Uvicorn 프로세스를 정리했습니다.")
        time.sleep(2)
    except Exception as e:
        print(f"   ℹ️ 프로세스 정리 중 오류 발생 (무시 가능): {e}")

    # Step 2: FastAPI 앱(Uvicorn) 백그라운드 실행
    try:
        command = [
            sys.executable,
            "-m",
            "uvicorn",
            f"{app_module_name}:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(port),
            "--reload",
        ]
        server_process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8"
        )
        print(f"   ⏳ FastAPI 서버를 포트 {port}에서 시작하는 중...")

        # 실시간 로그 출력을 위한 스레드 시작
        log_thread = threading.Thread(target=print_logs, args=(server_process, app_module_name))
        log_thread.daemon = True
        log_thread.start()
        print("   🔊 실시간 로그 출력을 시작합니다.")
        time.sleep(5)  # 서버가 완전히 시작될 때까지 잠시 대기

    except Exception as e:
        print(f"   ❌ FastAPI 서버 시작에 실패했습니다: {e}")
        return None, None

    # Step 3: 로컬 주소와 프로세스 반환
    local_url = f"http://localhost:{port}"
    print(f"✅ {app_module_name} 서버가 로컬({local_url})에서 성공적으로 실행되었습니다.")

    return local_url, server_process


print("✅ 'server_launcher.py' 파일이 [로컬 전용]으로 준비되었습니다.")
