# -*- coding: utf-8 -*-
"""Apply literal source material definitions without adopting legacy appearance.

The companion file records the actual A500 text rows and named source notes,
with page, PDF fingerprint and text boxes. A checked code definition does not
prove that every old element has been assigned the right code. Shared IDs that
mix pipes/devices remain unknown; narrow typed rules are recorded separately.
No model geometry, level, route, support or lifecycle value changes here.
"""
import collections
import copy
import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

DATA = os.path.join(os.path.dirname(__file__), 'data', 'source_material_review.json')
DISPLAY_KEYS = ('color', 'rough', 'metal', 'opacity', 'night', 'emissive',
                'emissiveIntensity', 'glow', 'transparent', 'transmission')


@lru_cache(maxsize=4)
def _guard_original_pdfs(entries):
    for path, expected, _mtime, _size in entries:
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise ValueError('Material literal original PDF changed: ' + path)
    return True


def _verify_original_pdfs(records):
    from lib import DL
    expected = {}
    for record in records.values():
        path = str(Path(DL) / record['source_pdf_file'])
        fingerprint = record['source_pdf_sha256']
        if path in expected and expected[path] != fingerprint:
            raise ValueError('Conflicting material source PDF fingerprints: ' + path)
        expected[path] = fingerprint
    entries = tuple((path, fingerprint, Path(path).stat().st_mtime_ns,
                     Path(path).stat().st_size)
                    for path, fingerprint in sorted(expected.items()))
    _guard_original_pdfs(entries)


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def apply(M):
    """Review every current physical material ID and strip legacy appearance.

    U.* keys belong to an explicitly defined display mode, not a physical
    material; they are left to display_palette. Old visual values remain in a
    historical field only. No RGB/RAL value is generated from color words.
    """
    with open(DATA, encoding='utf-8') as handle:
        data = json.load(handle)
    before_geometry = _hash([[e['id'], e['g']] for e in M['els']])
    records = data['source_records']
    _verify_original_pdfs(records)
    bindings = data['material_bindings']
    previous_review = M.get('materialReview', {})
    rows, counts = {}, collections.Counter()
    display_only, legacy_removed = [], 0
    for mid, mat in M.get('mats', {}).items():
        if mid.startswith('U.'):
            display_only.append(mid)
            continue
        historical = copy.deepcopy(mat.get('historical_definition') or
                                   data['historical_inventory']['mats'].get(mid) or mat)
        # Never treat the already reviewed/neutral name as the former design.
        for key in ('historical_definition', 'historical_display_parameters'):
            historical.pop(key, None)
        binding = bindings.get(mid, {})
        keys = binding.get('record_keys', [])
        source_rows = [records[key] for key in keys]
        status = binding.get('status', 'unknown_not_independently_reviewed')
        definition_checked = status == 'source_definition_checked'
        partial = status == 'source_rule_partial'
        literal = source_rows[0]['literal'] if source_rows and status not in (
            'mixed_physical_objects_do_not_assign_globally',) else 'unknown'
        material = source_rows[0]['source_material_literal'] if source_rows and (
            definition_checked or partial or status == 'source_conflict') else 'unknown'
        finish = source_rows[0]['source_finish_literal'] if source_rows and (
            definition_checked or partial) else 'unknown'
        color = source_rows[0]['physical_color_literal'] if source_rows and definition_checked else 'unknown'
        source_code = source_rows[0]['key'] if source_rows and status != 'mixed_physical_objects_do_not_assign_globally' else None
        row = {'id': mid, 'status': status, 'source_code': source_code,
               'source_literal': literal, 'source_material_literal': material,
               'source_finish_literal': finish, 'physical_color_literal': color,
               'physical_color_hex': None, 'source_record_keys': keys,
               'source_record_sha256': [q['record_sha256'] for q in source_rows],
               'source_refs': [q['source'] for q in source_rows],
               'typed_scope': binding.get('types'),
               'assignment_limit': binding.get('assignment_limit', 'No independent proof for this material assignment; unknown does not mean absent from all PDFs.'),
               'historical_display_color': historical.get('color'),
               'historical_name_not_authoritative': historical.get('name')}
        if binding.get('source_bound_element_ids'):
            expected = set(binding['source_bound_element_ids'])
            actual = {e['id'] for e in M['els'] if e.get('m') == mid}
            identities = all(e.get('t') in binding.get('types', [])
                             for e in M['els'] if e['id'] in expected)
            row['source_bound_element_ids'] = sorted(expected)
            row['literal_material_binding_verified'] = actual == expected and identities
            row['current_material_bound_element_count'] = len(actual)
            row['binding_limit'] = 'Named source parts and material literal only; full body, finish/color, Z, mounting, openings and operation are separate.'
        rows[mid] = row
        counts[status] += 1
        if any(key in mat for key in DISPLAY_KEYS):
            legacy_removed += 1
        for key in DISPLAY_KEYS:
            mat.pop(key, None)
        mat['historical_definition'] = historical
        mat['historical_display_color'] = historical.get('color')
        mat['historical_code_not_authoritative'] = historical.get('code')
        mat['historical_display_parameters'] = {k: copy.deepcopy(historical[k]) for k in DISPLAY_KEYS if k in historical}
        mat.update(copy.deepcopy({k: v for k, v in row.items() if k not in (
            'id', 'historical_name_not_authoritative', 'historical_display_color')}))
        mat['code'] = source_code or 'unknown'
        if definition_checked:
            mat['name'] = source_rows[0].get('literal_ar', literal)
        elif status == 'source_conflict':
            mat['name'] = 'مادة متعارضة في المصدر — ' + material
        elif partial:
            mat['name'] = 'قاعدة مصدر جزئية — ' + literal
        else:
            mat['name'] = 'وصف قديم غير معتمد — ' + historical.get('name', mid)
        mat['physical_appearance_note'] = 'النص الأصلي وحده هو دليل المادة/التشطيب/اللون. لاHEX/RAL مستخرج من كلمة أو CAD؛ قيم العرض القديمة تاريخية فقط. تعيين الكود لكل عنصر يحتاج شاهدًا منفصلًا.'
    # M.fin is a legacy tuple table used by the finish lens and cards. Replace
    # only its description/display color with the printed code definition.
    # The remaining BOQ/unit/quantity fields are preserved and marked as outside
    # this definition review; they never authorize material/placement/color.
    finish_rows = {}
    finishes = M.setdefault('fin', {})
    for code, record_key in data['finish_codes'].items():
        source = records[record_key]
        current = list(finishes.get(code, [None, None, None, None, None]))
        while len(current) < 5:
            current.append(None)
        old = previous_review.get('finish_definitions', {}).get(code, {})
        original = old.get('historical_fin_definition', copy.deepcopy(current))
        translated = source.get('literal_ar', source['literal'])
        current[0], current[1] = translated, None
        finishes[code] = current
        finish_rows[code] = {
            'code': code, 'source_record_key': record_key,
            'source_record_sha256': source['record_sha256'],
            'source': source['source'], 'source_literal': source['literal'],
            'source_description_ar': translated,
            'status': 'definition_checked_assignment_unverified',
            'physical_color_literal': source['physical_color_literal'],
            'physical_color_hex': None,
            'historical_fin_name': original[0],
            'historical_fin_hex': original[1],
            'historical_fin_definition': original,
            'other_tuple_fields_review': 'BOQ/unit/quantity are outside this A500 definition review; source verification remains separate.',
            'assignment_limit': 'تعريف كود من صف A500 فقط؛ لا يثبت تعيينه لكل عنصر أو الموافقة على اسم الحجر التجاري أو لون التنفيذ.'}
    # CSP without an ordinal is an existing analytical group, not a separately
    # printed A500 material. Preserve its identity and state that derivation.
    if 'CSP' in finishes:
        current = list(finishes['CSP'])
        old = previous_review.get('finish_definitions', {}).get('CSP', {})
        original = old.get('historical_fin_definition', copy.deepcopy(current))
        current[0], current[1] = 'مجموعة عرض مشتقة من CSP-2/CSP-3/CSP-4؛ ليست كودًا مستقلاً في A500', None
        finishes['CSP'] = current
        finish_rows['CSP'] = {'code': 'CSP', 'source_record_keys': [data['finish_codes'][q] for q in ('CSP-2', 'CSP-3', 'CSP-4')],
                              'source_description_ar': current[0], 'status': 'derived_analytical_group_not_printed_code',
                              'physical_color_literal': 'unknown', 'physical_color_hex': None,
                              'historical_fin_name': original[0], 'historical_fin_hex': original[1],
                              'historical_fin_definition': original,
                              'assignment_limit': 'تجميع عرض للرموز؛ لا مادة أو لون أو تعيين جديد.'}
    # BOQ really names OURO BRASIL. Show both primary-source definitions, rather
    # than calling that name invented or presenting it as the generic A500 row.
    type_text_review = copy.deepcopy(previous_review.get('type_finish_text_review', []))
    stair = M.get('types', {}).get('stair_step', {})
    for index, spec in enumerate(stair.get('sp', [])):
        if spec[0] != 'تشطيب النشرة والقائمة (BOQ 9.1.1.3)':
            continue
        original = copy.deepcopy(spec)
        stair['sp'][index] = ['تعريف F10 في A500؛ تعيين كل درجة يحتاج مصدرًا مستقلًا', records['A500:F10']['literal_ar']]
        stair['sp'].insert(index + 1, ['وصف BOQ ص9 حسب الموافقة؛ ليس لونًا أو اعتماد تعيين',
                                    'OURO BRASIL Granite؛ النشرة والبسطة3سم والقائمة2سم. الاسم التجاري مذكور في BOQ الخام؛ A500 يسمي جرانيت حسب الموافقة.'])
        if not any(q['type'] == 'stair_step' for q in type_text_review):
            type_text_review.append({'type': 'stair_step', 'historical_spec': original,
                                     'source_records': ['A500:F10', 'BOQ:F10'],
                                     'scope': 'Source definitions only; no stair geometry, assignment, approval or physical color changed.'})
        break
    after_geometry = _hash([[e['id'], e['g']] for e in M['els']])
    assert before_geometry == after_geometry
    stats = {'physical_material_ids': len(rows), 'counts': dict(counts),
             'textual_physical_color_ids': sum(q['physical_color_literal'] != 'unknown' for q in rows.values()),
             'source_rgb_hex_ral_ids': 0, 'display_only_ids': display_only,
             'legacy_display_definitions_removed_this_run': legacy_removed,
             'finish_code_definitions': len(data['finish_codes']),
             'finish_table_entries': len(finishes),
             'finish_rgb_hex_ral_ids': 0,
             'literal_source_records': len(records), 'geometry_preserved': True}
    M['materialReview'] = {'version': data['version'], 'counts': stats, 'materials': rows,
                           'finish_definitions': finish_rows,
                           'type_finish_text_review': type_text_review,
                           'source_comparisons': copy.deepcopy(data.get('source_comparisons', [])),
                           'conflicts': copy.deepcopy(data.get('conflicts', [])),
                           'typed_source_rules': copy.deepcopy(data['typed_source_rules']),
                           'external_report': 'pipeline/data/source_material_review.json',
                           'source_data_sha256': _hash(data),
                           'limit_ar': 'اتساق الملف القديم بلا سلطة تصميمية. هذه تعريفات مواد/أكواد من المصدر؛ لا تثبت تعيين كل عنصر أوZ أو مقاس التنفيذ. لون غير محدد=unknown،ولاRGB/RAL موروثًا.',
                           'geometry_preserved': True}
    M.setdefault('meta', {})['source_material_review'] = stats
    return M['materialReview']
