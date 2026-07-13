#!/usr/bin/env bash
# 皇甫谧数字人文平台 — P0 启动验证命令清单
# 执行方式: bash scripts/p0-verify.sh
set -e

echo "=============================="
echo "P0 启动验证"
echo "=============================="

echo ""
echo "--- 1. Docker 服务状态 ---"
docker compose -f docker-compose.dev.yml ps

echo ""
echo "--- 2. Backend /health ---"
curl -s -i http://127.0.0.1:8000/health | head -5

echo ""
echo "--- 3. Backend /ready ---"
curl -s http://127.0.0.1:8000/ready | python3 -m json.tool

echo ""
echo "--- 4. Frontend / ---"
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:5173/

echo ""
echo "--- 5. /api/v1/books (anonymous, should be 200) ---"
curl -s http://127.0.0.1:8000/api/v1/books | python3 -c "
import sys, json
d = json.load(sys.stdin)
items = d['data']['items']
print(f'total: {d[\"data\"][\"total\"]}, first book: {items[0][\"title\"] if items else \"NONE\"}')
"

echo ""
echo "--- 6. Login as researcher ---"
TOKEN=$(curl -s http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"researcher@huangfumi.org","password":"researcher123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")
echo "Token obtained: ${TOKEN:0:20}..."

echo ""
echo "--- 7. /api/v1/auth/me (researcher) ---"
curl -s http://127.0.0.1:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)['data']
print(f'user: {d[\"username\"]}, display_name: {d[\"display_name\"]}, roles: {[r[\"name\"] for r in d[\"roles\"]]}')
"

echo ""
echo "--- 8. Browse books as researcher ---"
curl -s http://127.0.0.1:8000/api/v1/books \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
items = d['data']['items']
print(f'total: {d[\"data\"][\"total\"]}')
for b in items[:3]:
    print(f'  - {b[\"title\"]} ({b[\"dynasty\"]})')
"

echo ""
echo "--- 9. Citation chain (SQL) ---"
PGPASSWORD=change-me psql -h 127.0.0.1 -U hfb -d hfb -c "
SELECT
    c.id::text as citation_id,
    e.id::text as evidence_id,
    p.id::text as passage_id,
    v.version_name
FROM citations c
JOIN evidences e ON c.evidence_id = e.id
JOIN passages p ON e.source_passage_id = p.id
JOIN versions v ON p.version_id = v.id
WHERE c.is_deleted=false AND e.is_deleted=false
  AND p.is_deleted=false AND v.is_deleted=false
LIMIT 3;
"

echo ""
echo "--- 10. DB counts ---"
PGPASSWORD=change-me psql -h 127.0.0.1 -U hfb -d hfb -c "
SELECT 'users' as tbl, count(*) FROM users WHERE is_deleted=false
UNION ALL SELECT 'roles', count(*) FROM roles WHERE is_deleted=false
UNION ALL SELECT 'books', count(*) FROM books WHERE is_deleted=false
UNION ALL SELECT 'versions', count(*) FROM versions WHERE is_deleted=false
UNION ALL SELECT 'passages', count(*) FROM passages WHERE is_deleted=false
UNION ALL SELECT 'documents', count(*) FROM documents WHERE is_deleted=false
UNION ALL SELECT 'document_chunks', count(*) FROM document_chunks WHERE is_deleted=false
UNION ALL SELECT 'evidences', count(*) FROM evidences WHERE is_deleted=false
UNION ALL SELECT 'citations', count(*) FROM citations WHERE is_deleted=false
ORDER BY tbl;
"

echo ""
echo "=============================="
echo "验证完成"
echo "=============================="
