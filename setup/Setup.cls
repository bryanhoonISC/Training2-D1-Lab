Include %occStatus

/// First-start setup of the interoperability lab (namespace INSURLIGENT).
///
/// setup/setup.script calls Run() through the container's -a hook, after IRIS
/// is live. By then the CPF merge has made the INSURLIGENT database and
/// namespace (interoperability on) and cleared the forced password change.
///
/// Run() loads the classes in src/ once. At the start of the lab, src/ has only
/// empty package folders. The ^Insurligent.Setup sentinel makes a restart a no-op.
Class Insurligent.Setup
{

/// Where the classes of src/ are inside the image.
Parameter SRCDIR = "/opt/insurligent/src";

ClassMethod Run() As %Status
{
	If $Data(^Insurligent.Setup) {
		Write "[insurligent-setup] already set up on ", ^Insurligent.Setup, " -- nothing to do.", !
		Return $$$OK
	}
	Write "[insurligent-setup] loading the classes in src/ ...", !
	Set tSC = $SYSTEM.OBJ.LoadDir(..#SRCDIR, "ck", , 1)
	If $$$ISERR(tSC) {
		Write "[insurligent-setup] note: some classes in src/ did not compile: ", $System.Status.GetErrorText(tSC), !
	}
	Set ^Insurligent.Setup = $ZDateTime($Horolog, 3)
	Write "[insurligent-setup] complete.", !
	Return $$$OK
}

}
