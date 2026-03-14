"""Testes dos endpoints de contas (empresas)."""
import uuid


def _account_payload(suffix=None, **extra):
    s = suffix or uuid.uuid4().hex[:8]
    return {
        "name": f"Empresa {s}",
        "segment": "technology",
        "size": "medium",
        "website": f"https://empresa{s}.com.br",
        "notes": "Nota de teste",
        **extra,
    }


# ──────────────────────────────────────────────────────────────────────────────
# POST /accounts
# ──────────────────────────────────────────────────────────────────────────────

async def test_create_account(client, admin_headers):
    r = await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)
    assert r.status_code == 201
    body = r.json()
    assert "id" in body
    assert body["is_active"] is True


async def test_create_account_response_structure(client, admin_headers):
    r = await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)
    body = r.json()
    for field in ("id", "name", "is_active", "contacts", "children", "created_at"):
        assert field in body


async def test_create_account_minimal_payload(client, admin_headers):
    suffix = uuid.uuid4().hex[:8]
    r = await client.post(
        "/api/v1/accounts",
        json={"name": f"Minimal {suffix}"},
        headers=admin_headers,
    )
    assert r.status_code == 201


async def test_create_account_with_address(client, admin_headers):
    payload = _account_payload()
    payload["address"] = {
        "street": "Rua Teste",
        "number": "100",
        "city": "São Paulo",
        "state": "SP",
        "zip_code": "01310-100",
        "country": "Brasil",
    }
    r = await client.post("/api/v1/accounts", json=payload, headers=admin_headers)
    assert r.status_code == 201
    assert r.json()["address"]["city"] == "São Paulo"


async def test_create_account_with_cnpj(client, admin_headers):
    cnpj = f"{uuid.uuid4().int % 100:02d}.{uuid.uuid4().int % 1000:03d}.{uuid.uuid4().int % 1000:03d}/0001-{uuid.uuid4().int % 100:02d}"
    r = await client.post(
        "/api/v1/accounts",
        json=_account_payload(cnpj=cnpj),
        headers=admin_headers,
    )
    assert r.status_code == 201


async def test_create_account_duplicate_cnpj(client, admin_headers):
    cnpj = "00.000.000/0001-00"
    await client.post("/api/v1/accounts", json=_account_payload(cnpj=cnpj), headers=admin_headers)
    r = await client.post("/api/v1/accounts", json=_account_payload(cnpj=cnpj), headers=admin_headers)
    assert r.status_code == 409


async def test_create_account_with_parent(client, admin_headers):
    parent = (await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)).json()
    r = await client.post(
        "/api/v1/accounts",
        json=_account_payload(parent_id=parent["id"]),
        headers=admin_headers,
    )
    assert r.status_code == 201


async def test_create_account_no_auth(client):
    r = await client.post("/api/v1/accounts", json=_account_payload())
    assert r.status_code == 401


async def test_create_account_no_permission(client, no_perm_headers):
    r = await client.post("/api/v1/accounts", json=_account_payload(), headers=no_perm_headers)
    assert r.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# GET /accounts
# ──────────────────────────────────────────────────────────────────────────────

async def test_list_accounts_empty(client, admin_headers):
    r = await client.get("/api/v1/accounts", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total"] == 0


async def test_list_accounts_returns_created(client, admin_headers):
    await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)
    r = await client.get("/api/v1/accounts", headers=admin_headers)
    assert r.json()["total"] >= 1


async def test_list_accounts_pagination(client, admin_headers):
    for _ in range(3):
        await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)
    r = await client.get("/api/v1/accounts?page=1&per_page=2", headers=admin_headers)
    body = r.json()
    assert body["per_page"] == 2
    assert len(body["items"]) <= 2


async def test_list_accounts_filter_by_name(client, admin_headers):
    suffix = uuid.uuid4().hex[:8]
    name = f"Filterable {suffix}"
    await client.post("/api/v1/accounts", json=_account_payload(name=name), headers=admin_headers)
    r = await client.get(f"/api/v1/accounts?name={name}", headers=admin_headers)
    assert r.status_code == 200
    assert any(i["name"] == name for i in r.json()["items"])


async def test_list_accounts_filter_by_cnpj(client, admin_headers):
    cnpj = "99.888.777/0001-66"
    await client.post("/api/v1/accounts", json=_account_payload(cnpj=cnpj), headers=admin_headers)
    r = await client.get(f"/api/v1/accounts?cnpj={cnpj}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 1


async def test_list_accounts_excludes_inactive_by_default(client, admin_headers):
    ap = await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)
    aid = ap.json()["id"]
    await client.delete(f"/api/v1/accounts/{aid}", headers=admin_headers)
    r = await client.get("/api/v1/accounts", headers=admin_headers)
    ids = [i["id"] for i in r.json()["items"]]
    assert aid not in ids


async def test_list_accounts_no_auth(client):
    r = await client.get("/api/v1/accounts")
    assert r.status_code == 401


async def test_list_accounts_no_permission(client, no_perm_headers):
    r = await client.get("/api/v1/accounts", headers=no_perm_headers)
    assert r.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# GET /accounts/{account_id}
# ──────────────────────────────────────────────────────────────────────────────

async def test_get_account_by_id(client, admin_headers):
    ap = await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)
    aid = ap.json()["id"]
    r = await client.get(f"/api/v1/accounts/{aid}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["id"] == aid


async def test_get_account_not_found(client, admin_headers):
    r = await client.get(f"/api/v1/accounts/{uuid.uuid4()}", headers=admin_headers)
    assert r.status_code == 404


async def test_get_account_no_auth(client, admin_headers):
    ap = await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)
    aid = ap.json()["id"]
    r = await client.get(f"/api/v1/accounts/{aid}")
    assert r.status_code == 401


async def test_get_account_no_permission(client, no_perm_headers, admin_headers):
    ap = await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)
    aid = ap.json()["id"]
    r = await client.get(f"/api/v1/accounts/{aid}", headers=no_perm_headers)
    assert r.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# PUT /accounts/{account_id}
# ──────────────────────────────────────────────────────────────────────────────

async def test_update_account(client, admin_headers):
    ap = await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)
    aid = ap.json()["id"]
    r = await client.put(
        f"/api/v1/accounts/{aid}",
        json={"name": "Updated Corp", "segment": "finance"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Updated Corp"
    assert r.json()["segment"] == "finance"


async def test_update_account_set_parent(client, admin_headers):
    parent = (await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)).json()
    child = (await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)).json()

    r = await client.put(
        f"/api/v1/accounts/{child['id']}",
        json={"parent_id": parent["id"]},
        headers=admin_headers,
    )
    assert r.status_code == 200


async def test_update_account_circular_hierarchy(client, admin_headers):
    """Atribuir filho como pai de si mesmo deve retornar 400."""
    parent = (await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)).json()
    child = (await client.post(
        "/api/v1/accounts",
        json=_account_payload(parent_id=parent["id"]),
        headers=admin_headers,
    )).json()

    r = await client.put(
        f"/api/v1/accounts/{parent['id']}",
        json={"parent_id": child["id"]},
        headers=admin_headers,
    )
    assert r.status_code == 400


async def test_update_account_not_found(client, admin_headers):
    r = await client.put(
        f"/api/v1/accounts/{uuid.uuid4()}",
        json={"name": "Ghost"},
        headers=admin_headers,
    )
    assert r.status_code == 404


async def test_update_account_no_permission(client, no_perm_headers, admin_headers):
    ap = await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)
    aid = ap.json()["id"]
    r = await client.put(
        f"/api/v1/accounts/{aid}",
        json={"name": "Hacked"},
        headers=no_perm_headers,
    )
    assert r.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# DELETE /accounts/{account_id}
# ──────────────────────────────────────────────────────────────────────────────

async def test_deactivate_account(client, admin_headers):
    ap = await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)
    aid = ap.json()["id"]
    r = await client.delete(f"/api/v1/accounts/{aid}", headers=admin_headers)
    assert r.status_code == 204

    gr = await client.get(f"/api/v1/accounts/{aid}", headers=admin_headers)
    assert gr.json()["is_active"] is False


async def test_deactivate_account_not_found(client, admin_headers):
    r = await client.delete(f"/api/v1/accounts/{uuid.uuid4()}", headers=admin_headers)
    assert r.status_code == 404


async def test_deactivate_account_already_inactive(client, admin_headers):
    ap = await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)
    aid = ap.json()["id"]
    await client.delete(f"/api/v1/accounts/{aid}", headers=admin_headers)
    r = await client.delete(f"/api/v1/accounts/{aid}", headers=admin_headers)
    assert r.status_code == 400


async def test_deactivate_account_no_auth(client, admin_headers):
    ap = await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)
    aid = ap.json()["id"]
    r = await client.delete(f"/api/v1/accounts/{aid}")
    assert r.status_code == 401


async def test_deactivate_account_no_permission(client, no_perm_headers, admin_headers):
    ap = await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)
    aid = ap.json()["id"]
    r = await client.delete(f"/api/v1/accounts/{aid}", headers=no_perm_headers)
    assert r.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# GET /accounts/{account_id}/hierarchy
# ──────────────────────────────────────────────────────────────────────────────

async def test_get_hierarchy_single_account(client, admin_headers):
    ap = await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)
    aid = ap.json()["id"]
    r = await client.get(f"/api/v1/accounts/{aid}/hierarchy", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == aid
    assert "children" in body


async def test_get_hierarchy_with_child(client, admin_headers):
    parent = (await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)).json()
    await client.post(
        "/api/v1/accounts",
        json=_account_payload(parent_id=parent["id"]),
        headers=admin_headers,
    )
    r = await client.get(f"/api/v1/accounts/{parent['id']}/hierarchy", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()["children"]) >= 1


async def test_get_hierarchy_deep_tree(client, admin_headers):
    grandparent = (await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)).json()
    parent = (await client.post(
        "/api/v1/accounts",
        json=_account_payload(parent_id=grandparent["id"]),
        headers=admin_headers,
    )).json()
    await client.post(
        "/api/v1/accounts",
        json=_account_payload(parent_id=parent["id"]),
        headers=admin_headers,
    )
    r = await client.get(f"/api/v1/accounts/{grandparent['id']}/hierarchy", headers=admin_headers)
    assert r.status_code == 200
    assert "children" in r.json()


async def test_get_hierarchy_not_found(client, admin_headers):
    r = await client.get(f"/api/v1/accounts/{uuid.uuid4()}/hierarchy", headers=admin_headers)
    assert r.status_code == 404


async def test_get_hierarchy_no_auth(client, admin_headers):
    ap = await client.post("/api/v1/accounts", json=_account_payload(), headers=admin_headers)
    aid = ap.json()["id"]
    r = await client.get(f"/api/v1/accounts/{aid}/hierarchy")
    assert r.status_code == 401
