/// GetPreAuthInfo_View reply (IRIS -> D1 Front): the patient from PAT-01 and the
/// insurer ID from Getinsurer. Flat on purpose: one JSON object, no nesting.
Class Insurligent.Interop.MSG.PreAuth.View.GetPreAuthInfoViewResponse Extends (Ens.Response, %JSON.Adaptor)
{

Property ResponseCode As %String(%JSONFIELDNAME = "response_code");

Property ResponseMessage As %String(%JSONFIELDNAME = "response_message", MAXLEN = 200);

Property HospitalNumber As %String(%JSONFIELDNAME = "hospital_number");

Property FirstName As %String(%JSONFIELDNAME = "first_name");

Property LastName As %String(%JSONFIELDNAME = "last_name");

Property BirthDate As %String(%JSONFIELDNAME = "birth_date");

Property Gender As %String(%JSONFIELDNAME = "gender");

Property InsurerId As %String(%JSONFIELDNAME = "insurer_id");

Property CompanyCode As %String(%JSONFIELDNAME = "company_code");

}
