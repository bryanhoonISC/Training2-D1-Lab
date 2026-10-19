/// GetPreAuthInfo_View request (D1 Front -> IRIS). Training: citizen ID search only.
/// IRIS checks the rules when it imports the JSON: [ Required ] and VALUELIST.
Class Insurligent.Interop.MSG.PreAuth.View.GetPreAuthInfoViewRequest Extends (Ens.Request, %JSON.Adaptor)
{

/// Only "CID" (Thai citizen ID) in the training flow.
Property SearchType As %String(%JSONFIELDNAME = "search_type", VALUELIST = ",CID") [ Required ];

Property IdentityNo As %String(%JSONFIELDNAME = "identity_no") [ Required ];

Property HospitalCode As %String(%JSONFIELDNAME = "hospital_code") [ Required ];

}
