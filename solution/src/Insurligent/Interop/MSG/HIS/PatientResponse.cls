/// Reply of the sub-BP BP.HIS.Patient: the patient from the PAT-01 reply.
/// ResponseCode is 200 (found) or 404 (not found).
Class Insurligent.Interop.MSG.HIS.PatientResponse Extends Ens.Response
{

Property ResponseCode As %String;

Property ResponseMessage As %String(MAXLEN = 200);

Property HospitalNumber As %String;

Property FirstName As %String;

Property LastName As %String;

Property BirthDate As %String;

Property Gender As %String;

}
