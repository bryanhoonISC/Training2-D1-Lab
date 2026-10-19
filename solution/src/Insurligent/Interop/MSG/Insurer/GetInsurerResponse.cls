/// Getinsurer reply (insurer -> IRIS). The BO imports the JSON reply into this class.
Class Insurligent.Interop.MSG.Insurer.GetInsurerResponse Extends (Ens.Response, %JSON.Adaptor)
{

Property ResponseCode As %String(%JSONFIELDNAME = "response_code");

Property ResponseMessage As %String(%JSONFIELDNAME = "response_message", MAXLEN = 200);

/// The nested JSON object "insured_person".
Property InsuredPerson As Insurligent.Interop.MSG.Type.InsuredPersonInfo(%JSONFIELDNAME = "insured_person");

}
