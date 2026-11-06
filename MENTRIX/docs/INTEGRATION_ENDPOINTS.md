# MENTRIX V1 local API routes

- `POST /api/student/login`
- `GET /api/student/session`
- `POST /api/student/logout`
- `POST /api/student/checkin`
- `GET /api/workspace/dashboard`
- `GET /api/workspace/courses`
- `GET /api/workspace/students`
- `POST /api/workspace/attendance/open`
- `GET /api/workspace/attendance/sessions`
- `GET /api/workspace/attendance/{session_id}/qr`
- `GET /api/workspace/attendance/{session_id}/register`
- `POST /api/workspace/attendance/{session_id}/random-check`
- `POST /api/workspace/attendance/{session_id}/mark`
- `POST /api/workspace/attendance/{session_id}/close`
- `GET /api/workspace/quizzes`
- `GET /api/workspace/quizzes/{quiz_id}`
- `POST /api/workspace/quizzes`
- `POST /api/workspace/quizzes/{quiz_id}/approve`
- `POST /api/workspace/materials/{course_id}`
- `GET /api/workspace/materials/{course_id}`
- `POST /api/workspace/papers/upload`
- `GET /api/workspace/papers`
- `GET /api/workspace/papers/{paper_id}`
- `GET /api/workspace/papers/{paper_id}/original`
- `POST /api/workspace/papers/{paper_id}/verify-and-grade`
- `POST /api/workspace/papers/{paper_id}/grades/{question_id}/review`
- `POST /api/workspace/papers/publish-batch`
- `POST /api/workspace/assistant/ask`
- `GET /api/workspace/experiments`
- `GET /api/workspace/experiments/report/{sprint}`
- `GET /api/workspace/audit`
- `GET /api/workspace/exports/grades.csv`
- `GET /api/workspace/exports/attendance.csv`

Authentication: `/api/auth/login` for TA/Admin; `/api/student/login` for student check-in only. All `/api/workspace/` routes require staff session. Student cookies are HttpOnly. API is a local pilot only.
