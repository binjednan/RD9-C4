"""Keep source audit inputs outside the rendered model without changing gates.

Only element source_* attributes are moved. Identity, source citations and the
live geometry remain in the model. Audit callers get a temporary attribute copy;
no saved geometry or computed pass result is ever restored from this file.
"""
import copy
import functools
import hashlib
import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent / 'data/source_audit_attributes.json'
SCHEMA = 'c4.source-audit-attributes.v1'
KEEP = frozenset(('source_page', 'source_sheet', 'source_set',
                  'source_reference', 'source_z_reference'))
META_KEY = 'source_audit_sidecar'
# Literal source keys read by existing gates, plus the source keys in the
# dynamically compared CSF.compile_after attributes and the stair review key.
# This is an input allowlist, not a new verification rule.
GATE_FIELDS = frozenset(('source_M_character', 'source_PDF_sha256', 'source_XY_verified', 'source_Z_conditional_envelope', 'source_Z_independently_checked_here', 'source_Z_mounting_and_physical_body_accepted', 'source_Z_verified', 'source_absolute_Z_physical_frame_material_mounting_accepted', 'source_absolute_Z_verified', 'source_anchor', 'source_anchor_deviation_cm', 'source_anchor_kind', 'source_anchor_pdf', 'source_anchors', 'source_angle', 'source_annotation', 'source_annotation_literal_or_bbox_differs', 'source_arc_glyph_composition_pending', 'source_assemblies', 'source_assembly_anchor_xy_checked', 'source_bbox_cm', 'source_bbox_dimensions_cm', 'source_bbox_pdf', 'source_bbox_pdf_pt', 'source_bearing_verified', 'source_binding_failures', 'source_binding_problems', 'source_binding_valid', 'source_board_identity', 'source_body_bbox_pdf', 'source_body_closed', 'source_body_component_index', 'source_body_group', 'source_body_kind', 'source_body_part_independently_drawn', 'source_body_pdf_points', 'source_body_primitives', 'source_body_verified', 'source_bound_primitives', 'source_boundary_part', 'source_boundary_pdf', 'source_boundary_xy_checked', 'source_capacity_l', 'source_chars', 'source_checked', 'source_checks', 'source_citation_index_schema', 'source_citation_text', 'source_clip_missing', 'source_clip_polygon', 'source_clip_procedural_Z', 'source_clip_raw_identity', 'source_closed_opening_bbox_cm', 'source_closed_profile_primitives', 'source_code', 'source_color_verified', 'source_colour_verified', 'source_complete_body_verified', 'source_component_class_differs', 'source_concrete_landing_top_bottom_m', 'source_conflict', 'source_conflict_stays_unresolved', 'source_conflicts', 'source_conflicts_resolved', 'source_contact_verified', 'source_context_drawings', 'source_context_word', 'source_copy_pose_xyz', 'source_copy_template_id', 'source_copy_template_max_float_delta_cm', 'source_correction_wave', 'source_curve_100_vs_1000_segment_hausdorff_cm', 'source_data_sha256', 'source_datum_boundaries_differ', 'source_datum_texttrace_or_bbox_differs', 'source_datums', 'source_derived_binding_status', 'source_derived_boundary_xy_checked', 'source_derived_historical_candidate', 'source_derived_historical_record', 'source_device_body_graphic_core', 'source_diameter_deviation_cm', 'source_dimension_literals', 'source_dimension_scope', 'source_dimensions_verified', 'source_disproved_element_remaining', 'source_disproved_extra_flight_retirement_and_undo_causal_HEAD_cut_only', 'source_disproved_flight_retirement_and_known_HEAD_cut_rollback_only', 'source_door_data_sha256', 'source_door_instance', 'source_door_paths', 'source_door_template', 'source_drawing', 'source_drawing_index', 'source_drawing_indices', 'source_drawing_operator_unexpected', 'source_drawings', 'source_edge_precision', 'source_faces', 'source_facts', 'source_family', 'source_file', 'source_finish_verified', 'source_finished_surface_Z_checked', 'source_fire_rating_accepted', 'source_fire_rating_literal_verified', 'source_footprint_derived', 'source_footprint_deviation', 'source_frame_depth_material_mounting_verified', 'source_frame_width_depth_verified', 'source_front_face_verified', 'source_full_wood_bbox_pdf', 'source_full_wood_profiles_pdf', 'source_gap_unverified_transform', 'source_generation_identity_sha256', 'source_generation_module', 'source_generic_subtype_pending', 'source_geometry_acceptance', 'source_geometry_review', 'source_glazing_bands', 'source_glyph_bbox_pdf', 'source_glyph_bounds_verified', 'source_glyph_checks', 'source_graphic_XY_checked', 'source_graphic_angle_checked', 'source_graphic_bbox_verified', 'source_graphic_body_extent_checked', 'source_graphic_dimensions_cm', 'source_graphic_family_verified', 'source_graphic_polygon_extent_checked', 'source_graphic_radius_not_body_dimension', 'source_graphic_rotation_verified', 'source_graphic_subtype_verified', 'source_group', 'source_guards_missing', 'source_hardware_verified', 'source_head_union_drawing_indices', 'source_heater_capacity_review', 'source_hinge_jamb_profile_pdf', 'source_hinge_side_anchor_pdf', 'source_hinge_side_anchor_xy_cm', 'source_holes_world', 'source_hvac_outlet_record', 'source_inner_drawing', 'source_inner_pdf_points', 'source_inner_xy', 'source_input_XY_checked', 'source_installation_quantity_acceptance', 'source_installation_status', 'source_installation_verified', 'source_installed_material_verified', 'source_inventory', 'source_inventory_complete', 'source_is_annotation', 'source_is_polygon', 'source_is_route', 'source_is_strip', 'source_jamb_bindings', 'source_joint_text_or_bbox_differs', 'source_key', 'source_kind', 'source_label', 'source_layer', 'source_layer_or_raw_operators_differ', 'source_leader_pdf_points', 'source_leader_primitives', 'source_leaders', 'source_ledger_identity_missing', 'source_length_deviation_cm', 'source_literal_dimensions_verified', 'source_literal_image_checks', 'source_literals', 'source_local_datums_verified', 'source_locked_xy', 'source_material_assignment_verified', 'source_material_class_literal', 'source_material_class_literal_only', 'source_material_class_literal_verified', 'source_material_class_verified', 'source_material_color_verified', 'source_material_verified', 'source_member_identity_scope', 'source_metadata', 'source_mount_face_verified', 'source_mount_verified', 'source_native_leaf_width_cm', 'source_nosing_pair', 'source_notes', 'source_opening_XY_mask_partial_slab_only', 'source_opening_XY_subtraction_only', 'source_opening_checks', 'source_opening_dimensions_literal_verified', 'source_opening_height_cm', 'source_opening_id', 'source_opening_ids', 'source_opening_plan_XY_checked', 'source_opening_plan_XY_verified', 'source_opening_still_filled', 'source_opening_width_cm', 'source_openings', 'source_operational_verified', 'source_opposite_jamb_profile_pdf', 'source_other_page', 'source_outer_XY_verified', 'source_outline_checks', 'source_page', 'source_page_facts', 'source_pages', 'source_pair_identity', 'source_pair_semantics', 'source_pairs', 'source_parser', 'source_part_height_verified', 'source_part_index', 'source_part_missing', 'source_pdf', 'source_pdf_centre', 'source_pdf_centre_pt', 'source_pdf_fingerprint', 'source_pdf_point', 'source_pdf_points', 'source_pdf_polygon', 'source_pdf_sha256', 'source_physical_acceptance', 'source_physical_body_verified', 'source_physical_color_verified', 'source_physical_hinge_pivot_verified', 'source_plan', 'source_plan_checks', 'source_plan_dimensions_literal_verified', 'source_plan_graphic_polygon_passed', 'source_plan_graphic_polygons', 'source_plan_polygon_deviation', 'source_plan_polygon_verified', 'source_plan_role', 'source_poly_index', 'source_polygon_deviation', 'source_polygon_invalid', 'source_ports_verified', 'source_position_pending_excluded', 'source_position_verified', 'source_power_kw', 'source_primitive', 'source_primitives', 'source_profile_deviation_cm', 'source_profile_passed', 'source_promotion', 'source_provenance_kind_differs', 'source_provision_markers', 'source_provision_only', 'source_provision_only_installation_unverified', 'source_raw_dash_parts_checked', 'source_raw_drawings', 'source_raw_items', 'source_raw_types', 'source_rebar_verified', 'source_record', 'source_record_binding_missing', 'source_record_sha256', 'source_reference', 'source_refs', 'source_registration', 'source_relative_envelope_checked', 'source_relative_height_verified', 'source_review_sha256', 'source_review_status', 'source_role', 'source_rotation_deg', 'source_rotation_matches_symbol', 'source_rotation_verified', 'source_schedule_text', 'source_schema', 'source_scope', 'source_scope_metadata', 'source_semantic_text', 'source_semantic_text_verified', 'source_semantics_checked', 'source_set', 'source_sheet', 'source_sheet_identity_differs', 'source_sheet_text', 'source_signed_open_vector_xy', 'source_slot', 'source_spec_texttraces', 'source_stair_concrete_review', 'source_status_counts', 'source_structural_XY_verified', 'source_structural_extent_verified', 'source_subtype_gap', 'source_subtype_pending', 'source_subtype_verified', 'source_summary', 'source_surface_Z_checked', 'source_surface_audit', 'source_symbol_angle_deg', 'source_tag', 'source_tag_hex_drawing', 'source_tag_texttrace', 'source_template_checks', 'source_text', 'source_texts', 'source_texttrace', 'source_texttrace_index', 'source_thickness_deviation', 'source_thickness_deviation_cm', 'source_thickness_literal_cm', 'source_trace_record', 'source_trace_review', 'source_trace_status', 'source_transform', 'source_transform_deviation_cm', 'source_transform_fresh_grid_policy', 'source_transform_mismatch', 'source_u_leaf_indices', 'source_vertex_indices', 'source_waist_verified', 'source_whole_assembly_verified', 'source_whole_cluster_xy', 'source_whole_leaf_XY_verified', 'source_window_group', 'source_window_member_identity', 'source_word_bbox_pdf_pt', 'source_word_index', 'source_word_layer', 'source_word_text', 'source_xy', 'source_xy_cm', 'source_xy_deviation_cm', 'source_xy_polygon', 'source_xy_polygon_cm', 'source_xy_verified', 'source_z_reference'))



def _bytes(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'),
                      sort_keys=True).encode('utf-8')


def _identity(e):
    return [e.get(k) for k in ('c', 't', 'l')]


@functools.lru_cache(maxsize=2)
def _read(path, mtime_ns, size):
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    if data.get('schema') != SCHEMA:
        raise ValueError('Unsupported source audit sidecar schema')
    return data, hashlib.sha256(raw).hexdigest()


def audit_model(M, data_path=None):
    """Hydrate missing source attributes only; preserve current geometry/values.

    Current attributes override saved inputs so editing a live attribute cannot
    be concealed by the sidecar. A compact model binds the file by SHA. The
    unchanged source gate still reopens the PDF and checks actual model g.
    """
    marker = M.get('meta', {}).get(META_KEY)
    # Ordinary full models keep the exact legacy behavior, including failures
    # for deliberately removed metadata. Only split_model marks compact input.
    if not marker:
        return M
    path = Path(data_path) if data_path is not None else DATA_PATH
    if not path.exists():
        if marker:
            raise ValueError('Required source audit sidecar is missing: '+str(path))
        return M
    stat = path.stat()
    data, digest = _read(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    if marker and marker.get('sha256') != digest:
        raise ValueError('Source audit sidecar SHA differs from compact model')
    records = data['records']
    # This returned value is a full audit/pipeline model. Drop the compact-input
    # marker on the copy so a later save captures fresh attributes rather than
    # reintroducing fields deliberately removed by a regeneration stage.
    metadata = dict(M.get('meta', {}))
    metadata.pop(META_KEY, None)
    out = dict(M, els=list(M['els']), meta=metadata)
    for i, e in enumerate(M['els']):
        rec = records.get(e['id'])
        if rec is None:
            continue
        current = e.get('a') or {}
        missing = set(rec['a']) - set(current)
        if not missing:
            continue
        if rec['identity'] != _identity(e):
            raise ValueError('Source audit sidecar identity differs: '+e['id'])
        attrs = copy.deepcopy(rec['a'])
        attrs.update(copy.deepcopy(current))
        out['els'][i] = dict(e, a=attrs)
    return out


def split_model(M, data_path=None):
    """Return compact copy and full gate inputs; never write model or geometry."""
    hydrated = audit_model(M, data_path)
    records = {}
    compact = dict(M, els=list(M['els']), meta=dict(M.get('meta', {})))
    for i, e in enumerate(hydrated['els']):
        attrs = e.get('a') or {}
        moved = {k: copy.deepcopy(v) for k, v in attrs.items()
                 if k.startswith('source_') and k not in KEEP}
        if moved:
            needed = {k: v for k, v in moved.items() if k in GATE_FIELDS}
            if needed:
                records[e['id']] = {'identity': _identity(e), 'a': needed}
            compact['els'][i] = dict(e, a={k: copy.deepcopy(v) for k, v in attrs.items()
                                        if k not in moved})
    data = {'schema': SCHEMA, 'records': records}
    raw = _bytes(data)
    compact['meta'][META_KEY] = {'file': 'pipeline/data/'+DATA_PATH.name,
        'sha256': hashlib.sha256(raw).hexdigest(), 'records': len(records)}
    return compact, data


def save_inputs_and_compact(M):
    """Save gate inputs at pipeline boundary, returning model for its caller to save."""
    compact, data = split_model(M)
    # The owner's temporary sidecar is bounded: new source proof cannot expand it.
    if M.get('meta',{}).get('owner_render_only') and DATA_PATH.exists():
        previous=json.loads(DATA_PATH.read_text())['records']
        data['records']={id:{'identity':rec['identity'],'a':{k:v for k,v in rec['a'].items() if k in previous[id]['a']}} for id,rec in data['records'].items() if id in previous}
        data['records']={id:rec for id,rec in data['records'].items() if rec['a']}
    raw = _bytes(data)
    if M.get('meta',{}).get('owner_render_only') and DATA_PATH.exists() and len(raw)>DATA_PATH.stat().st_size:
        raise ValueError('Owner forbids expanding the temporary source audit sidecar')
    compact['meta'][META_KEY].update(sha256=hashlib.sha256(raw).hexdigest(),records=len(data['records']))
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = DATA_PATH.with_suffix('.json.tmp')
    temporary.write_bytes(raw)
    temporary.replace(DATA_PATH)
    return compact
