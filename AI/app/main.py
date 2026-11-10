from fastapi import FastAPI

app = FastAPI(title="ai")


# BE의 GET /api/health와 같은 모양으로 둬서 배포 확인 스크립트가 같은 방식으로 읽게 한다.
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
