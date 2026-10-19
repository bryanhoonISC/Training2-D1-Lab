/// Request to the sub-BP BP.HIS.Patient: find one patient by citizen ID (PAT-01).
Class Insurligent.Interop.MSG.HIS.PatientRequest Extends Ens.Request
{

Property IdentityNo As %String [ Required ];

Property HospitalCode As %String [ Required ];

}
