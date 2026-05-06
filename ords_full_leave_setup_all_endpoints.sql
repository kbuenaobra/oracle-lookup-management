-- =========================================================
-- ORDS Full Leave App Setup Script
-- Schema:    APEXDEV
-- Alias:     /ords/hr/
-- Module:    leave
--
-- Endpoints:
--   GET  /ords/hr/leave/balance/:employee_id
--   GET  /ords/hr/leave/requests/:employee_id
--   POST /ords/hr/leave/request
--   POST /ords/hr/leave/request/:request_id/approve
--   POST /ords/hr/leave/request/:request_id/reject
--
-- Run in SQL Workshop as schema APEXDEV.
-- =========================================================


-- ---------------------------------------------------------
-- 1. Disable current ORDS mapping for schema
-- ---------------------------------------------------------
begin
    ords.enable_schema(
        p_enabled => false,
        p_schema  => 'APEXDEV'
    );
    commit;
end;
/


-- ---------------------------------------------------------
-- 2. Re-enable schema with alias "hr"
-- ---------------------------------------------------------
begin
    ords.enable_schema(
        p_enabled             => true,
        p_schema              => 'APEXDEV',
        p_url_mapping_type    => 'BASE_PATH',
        p_url_mapping_pattern => 'hr',
        p_auto_rest_auth      => false
    );
    commit;
end;
/


-- ---------------------------------------------------------
-- 3. Delete existing module if present
-- ---------------------------------------------------------
begin
    ords.delete_module(p_module_name => 'leave');
    commit;
exception
    when others then null;
end;
/


-- ---------------------------------------------------------
-- 4. Create module
-- ---------------------------------------------------------
begin
    ords.define_module(
        p_module_name    => 'leave',
        p_base_path      => '/leave/',
        p_items_per_page => 25,
        p_status         => 'PUBLISHED'
    );
    commit;
end;
/


-- ---------------------------------------------------------
-- 5. GET /ords/hr/leave/balance/:employee_id
--    Returns leave balances for an employee.
--    Test (browser): http://localhost:8888/ords/hr/leave/balance/2
-- ---------------------------------------------------------
begin
    ords.define_template(
        p_module_name => 'leave',
        p_pattern     => 'balance/:employee_id'
    );

    ords.define_handler(
        p_module_name => 'leave',
        p_pattern     => 'balance/:employee_id',
        p_method      => 'GET',
        p_source_type => ords.source_type_collection_feed,
        p_source      => q'[
            select
                leave_type_name,
                available_days
            from vw_leave_balances
            where employee_id = :employee_id
            order by leave_type_name
        ]'
    );

    commit;
end;
/


-- ---------------------------------------------------------
-- 6. GET /ords/hr/leave/requests/:employee_id
--    Returns all leave requests for an employee.
--    Test (browser): http://localhost:8888/ords/hr/leave/requests/2
-- ---------------------------------------------------------
begin
    ords.define_template(
        p_module_name => 'leave',
        p_pattern     => 'requests/:employee_id'
    );

    ords.define_handler(
        p_module_name => 'leave',
        p_pattern     => 'requests/:employee_id',
        p_method      => 'GET',
        p_source_type => ords.source_type_collection_feed,
        p_source      => q'[
            select
                request_id,
                employee_name,
                leave_type_name,
                start_date,
                end_date,
                total_days,
                reason,
                status,
                created_at
            from vw_leave_requests
            where employee_id = :employee_id
            order by created_at desc
        ]'
    );

    commit;
end;
/


-- ---------------------------------------------------------
-- 7. POST /ords/hr/leave/request
--    Creates a new leave request.
--    Test (curl):
--      curl -X POST "http://localhost:8888/ords/hr/leave/request?\
--        employee_id=2&leave_type_id=1&start_date=2026-05-10&\
--        end_date=2026-05-12&reason=Family%20trip"
-- ---------------------------------------------------------
begin
    ords.define_template(
        p_module_name => 'leave',
        p_pattern     => 'request'
    );

    ords.define_handler(
        p_module_name => 'leave',
        p_pattern     => 'request',
        p_method      => 'POST',
        p_source_type => ords.source_type_plsql,
        p_source      => q'[
declare
    l_request_id number;
    l_message    varchar2(4000);
begin
    leave_pkg.create_request(
        p_employee_id   => to_number(:employee_id),
        p_leave_type_id => to_number(:leave_type_id),
        p_start_date    => to_date(:start_date, 'YYYY-MM-DD'),
        p_end_date      => to_date(:end_date, 'YYYY-MM-DD'),
        p_reason        => :reason,
        p_request_id    => l_request_id,
        p_message       => l_message
    );

    owa_util.mime_header('application/json', false);
    htp.p('Cache-Control: no-cache');
    htp.p('Content-Type: application/json');
    owa_util.http_header_close;

    apex_json.initialize_clob_output;
    apex_json.open_object;
    apex_json.write('request_id', l_request_id);
    apex_json.write('message', l_message);
    apex_json.close_object;
    htp.p(apex_json.get_clob_output);
    apex_json.free_output;
end;
        ]'
    );

    commit;
end;
/


-- ---------------------------------------------------------
-- 8. POST /ords/hr/leave/request/:request_id/approve
--    Approves a pending leave request.
--    Test (curl):
--      curl -X POST "http://localhost:8888/ords/hr/leave/request/1/approve?\
--        action_by=1&remarks=Approved"
-- ---------------------------------------------------------
begin
    ords.define_template(
        p_module_name => 'leave',
        p_pattern     => 'request/:request_id/approve'
    );

    ords.define_handler(
        p_module_name => 'leave',
        p_pattern     => 'request/:request_id/approve',
        p_method      => 'POST',
        p_source_type => ords.source_type_plsql,
        p_source      => q'[
declare
    l_message varchar2(4000);
begin
    leave_pkg.approve_request(
        p_request_id => to_number(:request_id),
        p_action_by  => to_number(:action_by),
        p_remarks    => :remarks,
        p_message    => l_message
    );

    owa_util.mime_header('application/json', false);
    htp.p('Cache-Control: no-cache');
    htp.p('Content-Type: application/json');
    owa_util.http_header_close;

    apex_json.initialize_clob_output;
    apex_json.open_object;
    apex_json.write('request_id', to_number(:request_id));
    apex_json.write('message', l_message);
    apex_json.close_object;
    htp.p(apex_json.get_clob_output);
    apex_json.free_output;
end;
        ]'
    );

    commit;
end;
/


-- ---------------------------------------------------------
-- 9. POST /ords/hr/leave/request/:request_id/reject
--    Rejects a pending leave request.
--    Test (curl):
--      curl -X POST "http://localhost:8888/ords/hr/leave/request/1/reject?\
--        action_by=1&remarks=Insufficient%20team%20coverage"
-- ---------------------------------------------------------
begin
    ords.define_template(
        p_module_name => 'leave',
        p_pattern     => 'request/:request_id/reject'
    );

    ords.define_handler(
        p_module_name => 'leave',
        p_pattern     => 'request/:request_id/reject',
        p_method      => 'POST',
        p_source_type => ords.source_type_plsql,
        p_source      => q'[
declare
    l_message varchar2(4000);
begin
    leave_pkg.reject_request(
        p_request_id => to_number(:request_id),
        p_action_by  => to_number(:action_by),
        p_remarks    => :remarks,
        p_message    => l_message
    );

    owa_util.mime_header('application/json', false);
    htp.p('Cache-Control: no-cache');
    htp.p('Content-Type: application/json');
    owa_util.http_header_close;

    apex_json.initialize_clob_output;
    apex_json.open_object;
    apex_json.write('request_id', to_number(:request_id));
    apex_json.write('message', l_message);
    apex_json.close_object;
    htp.p(apex_json.get_clob_output);
    apex_json.free_output;
end;
        ]'
    );

    commit;
end;
/


-- ---------------------------------------------------------
-- 10. Verification queries
-- ---------------------------------------------------------
prompt ===== ORDS SCHEMA MAPPING =====
select parsing_schema,
       url_mapping_type,
       url_mapping_pattern,
       status
from user_ords_schemas;

prompt ===== ORDS MODULES =====
select module_name, uri_prefix, items_per_page, status
from user_ords_modules
order by module_name;

prompt ===== ORDS TEMPLATES =====
select module_name, pattern, priority
from user_ords_templates
order by module_name, pattern;

prompt ===== ORDS HANDLERS =====
select module_name, pattern, method, source_type
from user_ords_handlers
order by module_name, pattern, method;
