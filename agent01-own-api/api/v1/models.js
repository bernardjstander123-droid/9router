import {authorized,error} from '../../lib/security.js';
import {MODEL_ID,MODEL_SOURCE} from '../../lib/model.js';
export default function handler(req,res){
 res.setHeader('Cache-Control','no-store');
 if(req.method!=='GET')return error(res,405,'method_not_allowed','Use GET');
 if(!authorized(req))return error(res,401,'authentication_error','Valid Agent 01 API key required');
 return res.status(200).json({object:'list',data:[{id:MODEL_ID,object:'model',created:0,owned_by:'agent01',description:'Self-hosted '+MODEL_SOURCE+' CPU inference; no external model API key'}]});
}