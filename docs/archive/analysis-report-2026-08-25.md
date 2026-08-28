# GED_CRFPB - Complete System Analysis Report
**Date**: 2026-08-25 | **Status**: Ready for Implementation

---

## EXECUTIVE SUMMARY

Your system is a Django-based Document Management System (GED) with workflow routing (tramitação). The core architecture is sound, but there are **significant logic issues in the tramitação flow** and **a complete absence of first-password-change enforcement**.

### Critical Issues Found: 5
### Security Issues: 2  
### Logic/UX Issues: 8

---

## 1. ARCHITECTURE OVERVIEW

```
Stack:
├── Backend: Django 6.0.6 + Python
├── Frontend: Django Templates + Bootstrap 5 + HTMX
├── Database: SQLite
├── Storage: WhiteNoise + Filesystem (UNC paths)
└── Auth: Django default (User + custom Perfil)

Apps:
├── core/ - GED file management (filesystem-based)
├── tramitacao/ - Document routing workflow ← MOST ISSUES HERE
├── ecarta/ - External integration
└── setup/ - Project config
```

### Key Models
- **Perfil** (OneToOne User): Tracks user→sector but NO password_changed field
- **Tramitacao**: Main document record with status, can be modified during response
- **HistoricoTramitacao**: Tracks each step but doesn't prevent original data loss
- **AnexoTramitacao**: Attachments (appears functional)

---

## 2. FIRST PASSWORD CHANGE - MISSING ENTIRELY

### Problem
**No mechanism exists to force password change on first login.**

Current flow:
```
Admin creates user with password → User logs in → Immediate access to system
```

Required flow:
```
Admin creates user with password → User logs in → Redirect to password change → 
Must change password → Only then access system → Won't be asked again
```

### Security Risk
- Users can keep weak/default passwords forever
- No audit trail of password changes
- No enforcement of strong passwords on first login

### Solution Required
1. **Add field to Perfil model**: `password_changed` (Boolean, default=False)
2. **Create authentication middleware**: Check after login if password needs change
3. **Create password change view & template**: `/password/change/`
4. **Protect routes**: Both frontend redirect AND backend API checks
5. **Update session**: Mark user as password-changed after successful change

---

## 3. TRAMITACAO FLOW - CRITICAL ISSUES

### Issue T1: "Somente Envio" - Response Doesn't Reach Sender

#### Current Behavior
```
Step 1: User A (Setor 1) sends to User B (Setor 2)
  Tramitacao.setor_origem = Setor 1
  Tramitacao.setor_destino = Setor 2  
  Tramitacao.remetente = User A
  ✓ A sees in "Enviados" (filtered by setor_origem=1)
  ✓ B sees in "Recebidos" (filtered by setor_destino=2)

Step 2: User B responds
  CODE PROBLEM: responder_tramitacao() MODIFIES the original record!
  
  Tramitacao.setor_origem = Setor 2  ← CHANGED! Was Setor 1
  Tramitacao.setor_destino = Setor 1 ← Swapped correctly
  Tramitacao.remetente = User B      ← CHANGED! Was User A
  
  ✗ A can't find in "Enviados" (setor_origem=2, not 1)
  ✗ A can't find in "Recebidos" (setor_destino=1 but filter checks for both)
  ✓ B sees in "Enviados" (setor_origem=2)
```

#### Root Cause
**File: `tramitacao/services.py` line ~445**
```python
def responder_tramitacao(tramitacao, usuario, dados, arquivos):
    # ... validation ...
    tramitacao.setor_origem = setor_origem        # ← OVERWRITES!
    tramitacao.setor_destino = setor_destino
    tramitacao.remetente = usuario                # ← OVERWRITES!
    tramitacao.save()  # ← Saves changes to ORIGINAL record
```

#### Impact
- Original sender loses visibility of document
- Response status isn't tracked separately for each party
- Multiple responses in chain lose original sender completely
- Breaks audit trail

#### Solution
**Option A (Recommended)**: Keep original tramitacao immutable, add tracking fields
- Add: `remetente_original` (ForeignKey User)
- Add: `setor_origem_original` (ForeignKey Setor)
- Modify responder logic to preserve original and track current state separately
- Display logic uses original for "Enviados", current for "Recebidos"

**Option B**: Create separate Response record
- Less intrusive but more complex queries

---

### Issue T2: Setor Filter - All Users Shown Regardless of Selection

#### Current Behavior
1. Form loads with ALL users from database
2. User selects a setor
3. User selects a destinatário (but ALL users still visible)
4. No validation that selected user belongs to selected setor
5. Result: Can assign to user from wrong setor

#### Root Cause
**File: `tramitacao/forms.py` line ~25**
```python
def __init__(self, *args, **kwargs):
    # Populates ONCE at form load, doesn't refresh on setor change
    lista_usuarios = [(str(u.id), u.get_full_name() or u.username) 
                      for u in User.objects.all()]
    self.fields['usuario_destino'].choices = lista_usuarios
```

#### Paradox
- **AJAX endpoint EXISTS**: `ajax_usuarios_setores` (line 295 in views.py)
- Returns users filtered by setor
- But form validation doesn't use it

#### Impact
- Wrong recipients can be selected
- User confusion when filter doesn't work
- Data integrity issue

#### Solution
1. Keep all users in form (Django requirement)
2. Enable JavaScript to call `ajax_usuarios_setores` on setor change
3. Filter user dropdown on client side
4. Add server-side validation in `resolver_destinos_edicao()` to verify user→setor mapping
5. Reject request if user doesn't belong to setor

---

### Issue T3: Attachment Tracking

#### Current Status
- AnexoTramitacao links to Tramitacao AND HistoricoTramitacao
- HistoricoTramitacao created for each response step
- Upload path includes protocol: `tramitacoes/DD_MM_AAAA/protocol/filename`

#### Verification Needed
- ✓ After response: Appear to be preserved (via historico)
- ? After devolução: Need to test
- ? After reenvio: Need to test
- ? After assinatura: Need to verify signature doesn't remove attachments

#### Implementation
- Monitor that responder_tramitacao() correctly creates historico with attachments
- Verify devolução preserves attachment references
- Ensure reenvio (editar_tramitacao_devolvida) maintains links

---

### Issue T4 & T5: Aguardar Resposta - Logic Confusion

#### Problem 1: Field is BOOLEAN, not STATE
```python
aguardar_resposta = models.BooleanField(default=False)
# This is stored on Tramitacao.aguardar_resposta
# But what does it mean after a response?
# Original sender waits? Responder waits? Both?
```

#### Problem 2: Gets OVERWRITTEN on response
```python
# In responder_tramitacao():
tramitacao.aguardar_resposta = dados.get('aguardar_resposta', False)
# Original state ("I'm waiting for your response") is LOST
```

#### Problem 3: Multiple responses lose track
```
Send A→B (aguardar_resposta=True)  → B sees "waiting for response"
B responds to A (aguardar_resposta=False) → Response complete status unclear
C then needs to respond → Who's waiting? A or B? System doesn't know!
```

#### Solution
- Rename to `requer_resposta` or `exige_resposta` (requirement, not state)
- NEVER OVERWRITE this field, it's a requirement not a status
- Use separate `status` field to track current state
- Add to status machine: 'AGUARDANDO_RESPOSTA', 'RESPONDIDO'

---

### Issue T6: Assinatura Status

#### Current State: WORKING
- ✓ Exige assinatura field works
- ✓ User prompted for password to sign
- ✓ assinado flag set correctly
- ✓ Signature blocks completion if required

#### Concerns
- Interaction with resposta flow needs verification
- After resposta: does assinado flag get cleared? (Should it?)
- Signature + Resposta flow: do both rules work together?

#### Needed: Test with combined scenarios
- Sign then respond
- Respond then sign
- Require both sign and respond

---

### Issue T7: Assinatura + Resposta Modal

#### Current Implementation
```python
# tramitacao/services.py finalizar_tramitacao()
if tramitacao.aguardar_resposta:
    raise ValueError('Esta tramitação aguarda uma resposta antes da conclusão.')
```

#### UX Problem
- Error message shown as simple toast/alert
- Not prominent enough
- User might try repeatedly without understanding

#### Solution
- Create modal with:
  - Clear title: "Ação Bloqueada"
  - Icon: ⚠️ Exclamation in red
  - Message: "Esta tramitação ainda aguarda uma resposta antes da conclusão."
  - Call-to-action: "Responder" button or "Voltar" button
  - Match existing visual style (Bootstrap theme)

---

### Issue T8: Deadline Indicator - MISSING ENTIRELY

#### Current State
- ✓ Field exists: `data_limite_resposta` (DateField)
- ✗ NO visual indicator on UI
- ✗ NO deadline validation logic
- ✗ NO status tracking for deadline status

#### Required Implementation

1. **Add deadline status fields to Tramitacao**:
   - `prazo_status` (choices: ABERTO, PROXIMO, VENCIDO)
   - Auto-updated based on data_limite_resposta

2. **Display deadline in Recebidos tab**:
   ```html
   {% if t.data_limite_resposta %}
     <span class="badge bg-danger">
       <i class="bi bi-exclamation-triangle"></i>
       Resposta até {{ t.data_limite_resposta|date:"d/m/Y" }}
     </span>
   {% endif %}
   ```

3. **Add logic to check deadline**:
   - Days until deadline < 2: Yellow badge "PRAZO PRÓXIMO"
   - Today is deadline: Red badge "VENCIMENTO HOJE"  
   - Past deadline: Dark red badge "PRAZO VENCIDO"

4. **After response is received**:
   - Clear `aguardar_resposta` flag
   - Deadline indicator disappears
   - Status updates to show response received

5. **Visual hierarchy**:
   - Signature badge (already implemented)
   - Add deadline badge next to it
   - Use consistent icon/color scheme

---

## 4. SECURITY ISSUES

### S1: First Password Change Not Enforced ✗ CRITICAL
**Risk**: User keeps weak password forever
**Impact**: Authentication bypass potential
**Status**: Needs full implementation

### S2: Access Control During Response
**Current**: Receiving document auto-marks received, then pops modal for response
**Risk**: UI/logic mismatch - user might think response is optional
**Status**: Clarify flow with improved UI

### S3: Sector Filter Validation Missing
**Risk**: Wrong user can receive document
**Impact**: Data leakage between sectors
**Status**: Add backend validation

### S4: No Deadline Validation
**Risk**: Overdue responses still accepted without warning
**Impact**: SLA violations not tracked
**Status**: Add validation and indicators

---

## 5. DATABASE CHANGES NEEDED

### New Migration: Perfil Enhancement
```python
# Add to Perfil model
password_changed = models.BooleanField(default=False)
password_change_date = models.DateTimeField(null=True, blank=True)
```

### New Migration: Tramitacao Enhancement  
```python
# Add to Tramitacao model
remetente_original = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='tramitacoes_criadas_como_original')
setor_origem_original = models.ForeignKey(Setor, on_delete=models.SET_NULL, null=True, related_name='tramitacoes_origem_original')
prazo_status = models.CharField(max_length=20, choices=[('ABERTO', 'Aberto'), ('PROXIMO', 'Próximo'), ('VENCIDO', 'Vencido')], default='ABERTO')
requer_resposta = models.BooleanField(default=False)  # Rename from aguardar_resposta
```

---

## 6. AFFECTED FILES

### To Create
- `core/middleware.py` - Password change enforcement
- `core/templates/core/change_password.html` - Password change form
- `tramitacao/admin_actions.py` - Deadline status updates (optional)

### To Modify
- `core/models.py` - Add password_changed field
- `core/views.py` - Add password change view + login redirect logic
- `tramitacao/models.py` - Add tracking fields and deadline status
- `tramitacao/services.py` - Fix responder_tramitacao() logic
- `tramitacao/forms.py` - Add sector→user validation
- `tramitacao/views.py` - Add validation for sector→user
- `tramitacao/templates/tramitacao/caixa_entrada.html` - Add deadline indicators + improved modals
- `setup/settings.py` - Add middleware class

### Tests to Create/Update
- `core/tests.py` - First password change flow
- `tramitacao/tests.py` - Response routing, setor filter, deadline logic

---

## 7. IMPLEMENTATION ROADMAP

### Phase 1: Authentication (1-2 hours)
1. Add password_changed field to Perfil
2. Create migration
3. Implement password change view & template
4. Add middleware for enforcement
5. Update login flow

### Phase 2: Tramitacao - Response Routing (2-3 hours)
1. Add original tracking fields
2. Modify responder_tramitacao() logic
3. Update display queries
4. Test response chains
5. Verify attachments preserved

### Phase 3: Sector Filter (1 hour)
1. Enable JavaScript for AJAX user filtering
2. Add backend validation
3. Test with multiple sectors
4. Fix form submission

### Phase 4: Deadline Indicators (1-2 hours)
1. Add deadline fields & logic
2. Create visual components
3. Add deadline response clearing
4. Styling & UX polish

### Phase 5: Testing & Polish (1-2 hours)
1. Run test suite
2. Manual testing of all scenarios
3. Fix edge cases
4. Document changes

**Total Estimated Time**: 6-10 hours

---

## 8. TESTING CHECKLIST

### Authentication Tests
- [ ] New user created, force password change
- [ ] Try accessing internal route directly
- [ ] Password change successful, access granted
- [ ] Password change fails, user stays blocked
- [ ] Logout before password change, next login forces change again
- [ ] Next login after change doesn't force change again

### Tramitacao Flow Tests
- [ ] Send simple document, recipient responds (check sender can see response)
- [ ] Send with "aguardar resposta", multiple responses work
- [ ] Devolver then reenviar (sector filter works)
- [ ] Sector filter when editing returned document
- [ ] Attachments preserved through response
- [ ] Attachments preserved through devolver/reenviar
- [ ] Assinatura required + resposta required (both work together)
- [ ] Deadline approaching shows badge
- [ ] Deadline passed shows different badge
- [ ] After resposta, deadline badge disappears

### Security Tests
- [ ] Can't bypass password change with URL manipulation
- [ ] Can't call APIs without password change
- [ ] Session tokens respect password change requirement
- [ ] Wrong user can't be assigned to document
- [ ] Audit log tracks all password changes

---

## 9. RISKS & MITIGATION

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Changing tramitacao.remetente breaks existing records | Data corruption | Create data migration to populate new fields, test with backup |
| Middleware blocks legitimate users | System unavailable | Whitelist admin accounts, test on staging first |
| Response logic changes break existing workflows | Data loss | Create comprehensive tests before deploy, have rollback plan |
| Deadline logic breaks existing documents without dates | Display errors | Handle null dates gracefully, default to no deadline |

---

## 10. READY TO PROCEED

✓ Analysis complete
✓ Issues identified and prioritized  
✓ Solutions proposed
✓ Files to modify identified
✓ Test cases defined

**Next Step**: Implement fixes following the roadmap above, starting with Phase 1 (Authentication).

