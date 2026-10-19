/// Sub-BP (item BP.HIS.Patient): one PAT-01 query to the HIS.
/// It builds the HL7 query, calls the HL7 operation, and reads the reply.
/// Its caller sends a PatientRequest and gets a PatientResponse: no HL7.
Class Insurligent.Interop.BP.HISPatient Extends Ens.BusinessProcessBPL
{

XData BPL [ XMLNamespace = "http://www.intersystems.com/bpl" ]
{
<process language='objectscript' request='Insurligent.Interop.MSG.HIS.PatientRequest' response='Insurligent.Interop.MSG.HIS.PatientResponse' height='2000' width='2000' >
<context>
<property name='QBP' type='EnsLib.HL7.Message' instantiate='0' />
<property name='RSP' type='EnsLib.HL7.Message' instantiate='0' />
</context>
<sequence xend='200' yend='550' >
<transform name='Build QBP' class='Insurligent.Interop.DTL.PatientToQBP' source='request' target='context.QBP' xpos='200' ypos='250' />
<call name='Send PAT-01' target='BO.HIS.HL7' async='0' xpos='200' ypos='350' >
<request type='EnsLib.HL7.Message' >
<assign property="callrequest" value="context.QBP" action="set" />
</request>
<response type='EnsLib.HL7.Message' >
<assign property="context.RSP" value="callresponse" action="set" />
</response>
</call>
<transform name='Read RSP' class='Insurligent.Interop.DTL.RSPToPatient' source='context.RSP' target='response' xpos='200' ypos='450' />
</sequence>
</process>
}

}
