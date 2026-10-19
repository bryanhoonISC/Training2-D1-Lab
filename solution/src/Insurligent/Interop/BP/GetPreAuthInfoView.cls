/// Main BP (item BP.GetPreAuthInfoView): GetPreAuthInfo_View for a citizen ID.
/// 1. It calls the sub-BP BP.HIS.Patient (PAT-01) and copies the patient into the reply.
/// 2. If the patient is found, it calls BO.Insurer.REST (Getinsurer, company AIA).
Class Insurligent.Interop.BP.GetPreAuthInfoView Extends Ens.BusinessProcessBPL
{

XData BPL [ XMLNamespace = "http://www.intersystems.com/bpl" ]
{
<process language='objectscript' request='Insurligent.Interop.MSG.PreAuth.View.GetPreAuthInfoViewRequest' response='Insurligent.Interop.MSG.PreAuth.View.GetPreAuthInfoViewResponse' height='2000' width='2000' >
<sequence xend='200' yend='550' >
<call name='Get patient (PAT-01)' target='BP.HIS.Patient' async='0' xpos='200' ypos='250' >
<request type='Insurligent.Interop.MSG.HIS.PatientRequest' >
<assign property="callrequest.IdentityNo" value="request.IdentityNo" action="set" />
<assign property="callrequest.HospitalCode" value="request.HospitalCode" action="set" />
</request>
<response type='Insurligent.Interop.MSG.HIS.PatientResponse' >
<assign property="response.ResponseCode" value="callresponse.ResponseCode" action="set" />
<assign property="response.ResponseMessage" value="callresponse.ResponseMessage" action="set" />
<assign property="response.HospitalNumber" value="callresponse.HospitalNumber" action="set" />
<assign property="response.FirstName" value="callresponse.FirstName" action="set" />
<assign property="response.LastName" value="callresponse.LastName" action="set" />
<assign property="response.BirthDate" value="callresponse.BirthDate" action="set" />
<assign property="response.Gender" value="callresponse.Gender" action="set" />
</response>
</call>
<if name='Patient found?' condition='response.ResponseCode="200"' xpos='200' ypos='350' xend='200' yend='450' >
<true>
<call name='Getinsurer' target='BO.Insurer.REST' async='0' xpos='335' ypos='500' >
<request type='Insurligent.Interop.MSG.Insurer.GetInsurerRequest' >
<assign property="callrequest.IdentityType" value="&quot;CID&quot;" action="set" />
<assign property="callrequest.IdentityNo" value="request.IdentityNo" action="set" />
<assign property="callrequest.CompanyCode" value="&quot;AIA&quot;" action="set" />
</request>
<response type='Insurligent.Interop.MSG.Insurer.GetInsurerResponse' >
<assign property="response.InsurerId" value="callresponse.InsuredPerson.InsurerId" action="set" />
<assign property="response.CompanyCode" value="$Select(callresponse.ResponseCode=&quot;200&quot;:&quot;AIA&quot;,1:&quot;&quot;)" action="set" />
</response>
</call>
</true>
</if>
</sequence>
</process>
}

}
