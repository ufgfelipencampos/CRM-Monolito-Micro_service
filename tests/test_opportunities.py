"""Testes dos endpoints de oportunidades e pipeline."""
import uuid
from datetime import date, timedelta


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

async def _make_stage(client, admin_headers, order=1, probability="25.00"):
    r = await client.post(
        "/api/v1/pipeline/stages",
        json={"name": f"Stage {uuid.uuid4().hex[:6]}", "order": order, "probability": probability},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _make_contact(client, admin_headers):
    suffix = uuid.uuid4().hex[:8]
    r = await client.post(
        "/api/v1/contacts",
        json={"name": f"OppContact {suffix}", "email": f"oppcontact_{suffix}@test.com"},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _make_account(client, admin_headers):
    suffix = uuid.uuid4().hex[:8]
    r = await client.post(
        "/api/v1/accounts",
        json={"name": f"OppAccount {suffix}"},
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _make_opportunity(client, admin_headers, stage_id, contact_id, account_id, **extra):
    close_date = (date.today() + timedelta(days=30)).isoformat()
    r = await client.post(
        "/api/v1/opportunities",
        json={
            "title": f"Opp {uuid.uuid4().hex[:6]}",
            "stage_id": stage_id,
            "contact_id": contact_id,
            "account_id": account_id,
            "value": "5000.00",
            "close_date": close_date,
            "probability": "75.00",
            "source": "website",
            **extra,
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


# ──────────────────────────────────────────────────────────────────────────────
# POST /pipeline/stages
# ──────────────────────────────────────────────────────────────────────────────

async def test_create_pipeline_stage(client, admin_headers):
    r = await client.post(
        "/api/v1/pipeline/stages",
        json={"name": "Prospecção", "order": 1, "probability": "10.00"},
        headers=admin_headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert "id" in body
    assert body["is_active"] is True
    assert body["name"] == "Prospecção"


async def test_create_pipeline_stage_response_structure(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    for field in ("id", "name", "order", "probability", "is_active", "created_at"):
        assert field in stage


async def test_create_pipeline_stage_no_auth(client):
    r = await client.post(
        "/api/v1/pipeline/stages",
        json={"name": "X", "order": 1, "probability": "0"},
    )
    assert r.status_code == 401


async def test_create_pipeline_stage_no_permission(client, no_perm_headers):
    r = await client.post(
        "/api/v1/pipeline/stages",
        json={"name": "X", "order": 1, "probability": "0"},
        headers=no_perm_headers,
    )
    assert r.status_code == 403


async def test_create_pipeline_stage_invalid_probability(client, admin_headers):
    r = await client.post(
        "/api/v1/pipeline/stages",
        json={"name": "Bad", "order": 1, "probability": "150.00"},
        headers=admin_headers,
    )
    assert r.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# GET /pipeline/stages
# ──────────────────────────────────────────────────────────────────────────────

async def test_list_pipeline_stages(client, admin_headers):
    await _make_stage(client, admin_headers)
    r = await client.get("/api/v1/pipeline/stages", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) >= 1


async def test_list_pipeline_stages_ordered(client, admin_headers):
    await _make_stage(client, admin_headers, order=3)
    await _make_stage(client, admin_headers, order=1)
    await _make_stage(client, admin_headers, order=2)
    r = await client.get("/api/v1/pipeline/stages", headers=admin_headers)
    orders = [s["order"] for s in r.json()]
    assert orders == sorted(orders)


async def test_list_pipeline_stages_no_auth(client):
    r = await client.get("/api/v1/pipeline/stages")
    assert r.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# PUT /pipeline/stages/{stage_id}
# ──────────────────────────────────────────────────────────────────────────────

async def test_update_pipeline_stage(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    r = await client.put(
        f"/api/v1/pipeline/stages/{stage['id']}",
        json={"name": "Negociação Avançada", "probability": "80.00"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Negociação Avançada"


async def test_update_stage_not_found(client, admin_headers):
    r = await client.put(
        f"/api/v1/pipeline/stages/{uuid.uuid4()}",
        json={"name": "Ghost"},
        headers=admin_headers,
    )
    assert r.status_code == 404


async def test_deactivate_stage_with_active_opportunities_fails(client, admin_headers):
    """Não é possível desativar estágio com oportunidades ativas."""
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    await _make_opportunity(client, admin_headers, stage["id"], contact["id"], account["id"])

    r = await client.put(
        f"/api/v1/pipeline/stages/{stage['id']}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert r.status_code == 400


async def test_deactivate_stage_without_opportunities_succeeds(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    r = await client.put(
        f"/api/v1/pipeline/stages/{stage['id']}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False


# ──────────────────────────────────────────────────────────────────────────────
# POST /opportunities
# ──────────────────────────────────────────────────────────────────────────────

async def test_create_opportunity(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    opp = await _make_opportunity(client, admin_headers, stage["id"], contact["id"], account["id"])
    assert opp["status"] == "active"
    assert "id" in opp


async def test_create_opportunity_response_structure(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    opp = await _make_opportunity(client, admin_headers, stage["id"], contact["id"], account["id"])
    for field in ("id", "title", "status", "stage", "contact", "account", "created_at"):
        assert field in opp


async def test_create_opportunity_invalid_stage(client, admin_headers):
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    r = await client.post(
        "/api/v1/opportunities",
        json={
            "title": "Bad Stage",
            "stage_id": str(uuid.uuid4()),
            "contact_id": contact["id"],
            "account_id": account["id"],
            "close_date": (date.today() + timedelta(days=10)).isoformat(),
        },
        headers=admin_headers,
    )
    assert r.status_code == 404


async def test_create_opportunity_no_auth(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    r = await client.post(
        "/api/v1/opportunities",
        json={
            "title": "No Auth Opp",
            "stage_id": stage["id"],
            "contact_id": contact["id"],
            "account_id": account["id"],
            "close_date": (date.today() + timedelta(days=10)).isoformat(),
        },
    )
    assert r.status_code == 401


async def test_create_opportunity_no_permission(client, admin_headers, no_perm_headers):
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    r = await client.post(
        "/api/v1/opportunities",
        json={
            "title": "No Perm Opp",
            "stage_id": stage["id"],
            "contact_id": contact["id"],
            "account_id": account["id"],
            "close_date": (date.today() + timedelta(days=10)).isoformat(),
        },
        headers=no_perm_headers,
    )
    assert r.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# GET /opportunities
# ──────────────────────────────────────────────────────────────────────────────

async def test_list_opportunities_empty(client, admin_headers):
    r = await client.get("/api/v1/opportunities", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total"] == 0


async def test_list_opportunities(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    await _make_opportunity(client, admin_headers, stage["id"], contact["id"], account["id"])
    r = await client.get("/api/v1/opportunities", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 1


async def test_list_opportunities_filter_by_status_active(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    await _make_opportunity(client, admin_headers, stage["id"], contact["id"], account["id"])
    r = await client.get("/api/v1/opportunities?status=active", headers=admin_headers)
    for item in r.json()["items"]:
        assert item["status"] == "active"


async def test_list_opportunities_filter_by_status_won(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    opp = await _make_opportunity(client, admin_headers, stage["id"], contact["id"], account["id"])
    await client.patch(
        f"/api/v1/opportunities/{opp['id']}/close",
        json={"status": "won"},
        headers=admin_headers,
    )
    r = await client.get("/api/v1/opportunities?status=won", headers=admin_headers)
    assert r.json()["total"] >= 1
    for item in r.json()["items"]:
        assert item["status"] == "won"


async def test_list_opportunities_filter_by_stage(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    await _make_opportunity(client, admin_headers, stage["id"], contact["id"], account["id"])
    r = await client.get(f"/api/v1/opportunities?stage_id={stage['id']}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 1


async def test_list_opportunities_no_auth(client):
    r = await client.get("/api/v1/opportunities")
    assert r.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# GET /opportunities/{opp_id}
# ──────────────────────────────────────────────────────────────────────────────

async def test_get_opportunity_by_id(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    opp = await _make_opportunity(client, admin_headers, stage["id"], contact["id"], account["id"])
    r = await client.get(f"/api/v1/opportunities/{opp['id']}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["id"] == opp["id"]


async def test_get_opportunity_not_found(client, admin_headers):
    r = await client.get(f"/api/v1/opportunities/{uuid.uuid4()}", headers=admin_headers)
    assert r.status_code == 404


async def test_get_opportunity_no_auth(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    opp = await _make_opportunity(client, admin_headers, stage["id"], contact["id"], account["id"])
    r = await client.get(f"/api/v1/opportunities/{opp['id']}")
    assert r.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# PUT /opportunities/{opp_id}
# ──────────────────────────────────────────────────────────────────────────────

async def test_update_opportunity(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    opp = await _make_opportunity(client, admin_headers, stage["id"], contact["id"], account["id"])
    r = await client.put(
        f"/api/v1/opportunities/{opp['id']}",
        json={"title": "Updated Title", "value": "9999.00"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["title"] == "Updated Title"


async def test_update_closed_opportunity_fails(client, admin_headers):
    """Oportunidade fechada não pode ser atualizada."""
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    opp = await _make_opportunity(client, admin_headers, stage["id"], contact["id"], account["id"])
    await client.patch(
        f"/api/v1/opportunities/{opp['id']}/close",
        json={"status": "won"},
        headers=admin_headers,
    )
    r = await client.put(
        f"/api/v1/opportunities/{opp['id']}",
        json={"title": "Cannot Update"},
        headers=admin_headers,
    )
    assert r.status_code == 400


async def test_update_opportunity_not_found(client, admin_headers):
    r = await client.put(
        f"/api/v1/opportunities/{uuid.uuid4()}",
        json={"title": "Ghost"},
        headers=admin_headers,
    )
    assert r.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# PATCH /opportunities/{opp_id}/stage
# ──────────────────────────────────────────────────────────────────────────────

async def test_move_opportunity_stage(client, admin_headers):
    stage1 = await _make_stage(client, admin_headers, order=1)
    stage2 = await _make_stage(client, admin_headers, order=2)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    opp = await _make_opportunity(client, admin_headers, stage1["id"], contact["id"], account["id"])

    r = await client.patch(
        f"/api/v1/opportunities/{opp['id']}/stage",
        json={"stage_id": stage2["id"]},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["stage"]["id"] == stage2["id"]


async def test_move_closed_opportunity_stage_fails(client, admin_headers):
    stage1 = await _make_stage(client, admin_headers, order=1)
    stage2 = await _make_stage(client, admin_headers, order=2)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    opp = await _make_opportunity(client, admin_headers, stage1["id"], contact["id"], account["id"])
    await client.patch(
        f"/api/v1/opportunities/{opp['id']}/close",
        json={"status": "won"},
        headers=admin_headers,
    )
    r = await client.patch(
        f"/api/v1/opportunities/{opp['id']}/stage",
        json={"stage_id": stage2["id"]},
        headers=admin_headers,
    )
    assert r.status_code == 400


async def test_move_opportunity_stage_not_found_opp(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    r = await client.patch(
        f"/api/v1/opportunities/{uuid.uuid4()}/stage",
        json={"stage_id": stage["id"]},
        headers=admin_headers,
    )
    assert r.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# PATCH /opportunities/{opp_id}/close
# ──────────────────────────────────────────────────────────────────────────────

async def test_close_opportunity_won(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    opp = await _make_opportunity(client, admin_headers, stage["id"], contact["id"], account["id"])

    r = await client.patch(
        f"/api/v1/opportunities/{opp['id']}/close",
        json={"status": "won"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "won"
    assert body["closed_at"] is not None


async def test_close_opportunity_lost_with_reason(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    opp = await _make_opportunity(client, admin_headers, stage["id"], contact["id"], account["id"])

    r = await client.patch(
        f"/api/v1/opportunities/{opp['id']}/close",
        json={"status": "lost", "lost_reason": "Concorrente com preço menor"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "lost"
    assert body["lost_reason"] == "Concorrente com preço menor"


async def test_close_opportunity_lost_without_reason_fails(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    opp = await _make_opportunity(client, admin_headers, stage["id"], contact["id"], account["id"])

    r = await client.patch(
        f"/api/v1/opportunities/{opp['id']}/close",
        json={"status": "lost"},
        headers=admin_headers,
    )
    assert r.status_code == 400


async def test_close_already_closed_opportunity_fails(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    opp = await _make_opportunity(client, admin_headers, stage["id"], contact["id"], account["id"])
    await client.patch(
        f"/api/v1/opportunities/{opp['id']}/close",
        json={"status": "won"},
        headers=admin_headers,
    )
    r = await client.patch(
        f"/api/v1/opportunities/{opp['id']}/close",
        json={"status": "won"},
        headers=admin_headers,
    )
    assert r.status_code == 400


async def test_close_opportunity_not_found(client, admin_headers):
    r = await client.patch(
        f"/api/v1/opportunities/{uuid.uuid4()}/close",
        json={"status": "won"},
        headers=admin_headers,
    )
    assert r.status_code == 404


async def test_close_opportunity_no_auth(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    opp = await _make_opportunity(client, admin_headers, stage["id"], contact["id"], account["id"])
    r = await client.patch(
        f"/api/v1/opportunities/{opp['id']}/close",
        json={"status": "won"},
    )
    assert r.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# GET /pipeline  (Kanban view)
# ──────────────────────────────────────────────────────────────────────────────

async def test_get_pipeline_view_empty(client, admin_headers):
    r = await client.get("/api/v1/pipeline", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert "columns" in body
    assert isinstance(body["columns"], list)


async def test_get_pipeline_view_with_opportunity(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    await _make_opportunity(client, admin_headers, stage["id"], contact["id"], account["id"])

    r = await client.get("/api/v1/pipeline", headers=admin_headers)
    assert r.status_code == 200
    columns = r.json()["columns"]
    stage_ids = [col["stage"]["id"] for col in columns]
    assert stage["id"] in stage_ids


async def test_get_pipeline_view_column_has_correct_count(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    await _make_opportunity(client, admin_headers, stage["id"], contact["id"], account["id"])
    await _make_opportunity(client, admin_headers, stage["id"], contact["id"], account["id"])

    r = await client.get("/api/v1/pipeline", headers=admin_headers)
    columns = r.json()["columns"]
    col = next(c for c in columns if c["stage"]["id"] == stage["id"])
    assert col["count"] == 2
    assert "total_value" in col


async def test_get_pipeline_view_excludes_closed_opportunities(client, admin_headers):
    stage = await _make_stage(client, admin_headers)
    contact = await _make_contact(client, admin_headers)
    account = await _make_account(client, admin_headers)
    opp = await _make_opportunity(client, admin_headers, stage["id"], contact["id"], account["id"])
    await client.patch(
        f"/api/v1/opportunities/{opp['id']}/close",
        json={"status": "won"},
        headers=admin_headers,
    )

    r = await client.get("/api/v1/pipeline", headers=admin_headers)
    columns = r.json()["columns"]
    col = next((c for c in columns if c["stage"]["id"] == stage["id"]), None)
    if col:
        assert col["count"] == 0


async def test_get_pipeline_view_no_auth(client):
    r = await client.get("/api/v1/pipeline")
    assert r.status_code == 401


async def test_get_pipeline_view_no_permission(client, no_perm_headers):
    r = await client.get("/api/v1/pipeline", headers=no_perm_headers)
    assert r.status_code == 403
