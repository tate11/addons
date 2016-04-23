from openerp import tools
from openerp.osv import fields,osv
import openerp.addons.decimal_precision as dp
import time
import logging
from openerp.tools.translate import _
from datetime import datetime

_logger = logging.getLogger(__name__)

CUST_MAPPING = {
	"policy_no"			: "arg_nomor_polis",
	"product_class"		: "arg_class",
	"subclass"			: "arg_subclass",
	"eff_date"			: "arg_eff_date",
	"exp_date"			: "arg_exp_date",
	"cust_code"			: "arg_cust_code",
	"cust_fullname"		: "name",
	"qq"				: "arg_qq",
	"cust_cp"			: "arg_cp",
	"cust_addr_1"		: "street",
	"cust_addr_2"		: "street2",
	"cust_city"			: "city",
	"cust_postal_code"	: "zip",
	"cust_country_name"	: "country_id",
	"cust_province"		: "state_id",
}

COMPANY_MAPPING = {
	"company_code"		: "cif",
	"company_name"		: "name",
	"company_type"		: None,
}

AGENT_MAPPING = {
	"marketing_code"	: "cif",
	"marketing_name"	: "name",
	
}

####################################################################
# partner data
# from arg-customer csv file
####################################################################
class import_arg(osv.osv): 
	_name 		= "reliance.import_arg"
	_columns 	= {
		"policy_no"			:	fields.char("POLICY_NO", select=1),
		"product_class"		:	fields.char("CLASS"),
		"subclass"			:	fields.char("SUBCLASS"),
		"eff_date"			:	fields.char("EFF_DATE"),
		"exp_date"			:	fields.char("EXP_DATE"),
		"company_code"		:	fields.char("COMPANY_CODE"),
		"company_name"		:	fields.char("COMPANY_NAME"),
		"company_type"		:	fields.char("COMPANY_TYPE"),
		"marketing_code"	:	fields.char("MARKETING_CODE"),
		"marketing_name"	:	fields.char("MARKETING_NAME"),
		"cust_code"			:	fields.char("CUST_CODE"),
		"cust_name"			:	fields.char("CUST_NAME"),
		"cust_fullname"		:	fields.char("CUST_FULLNAME"),
		"qq"				:	fields.char("QQ"),
		"cust_cp"			:	fields.char("CUST_CP"),
		"cust_addr_1"		:	fields.char("CUST_ADDR_1"),
		"cust_addr_2"		:	fields.char("CUST_ADDR_2"),
		"cust_city"			:	fields.char("CUST_CITY"),
		"cust_postal_code"	:	fields.char("CUST_POSTAL_CODE"),
		"cust_province"		:	fields.char("CUST_PROVINCE"),
		"cust_country_name"	:	fields.char("CUST_COUNTRY_NAME"),

		"status_policy"		:	fields.char("STATUS_POLICY"),
		"source_of_business":	fields.char("SOURCE_OF_BUSINESS"), 

		'is_imported' 		: 	fields.boolean("Imported to Partner?", select=1),
		"notes"				:	fields.char("Notes"),
	}

	def action_import_partner(self, cr, uid, context=None):
		active_ids = context and context.get('active_ids', False)
		if not context:
			context = {}

		self.actual_import(cr, uid, active_ids, context=context)


	def cron_import_partner(self, cr, uid, context=None):
		arg_import_partner_limit = self.pool.get('ir.config_parameter').get_param(cr, uid, 'arg_import_partner_limit')
		_logger.warning('running cron arg_import_partner, limit=%s' % arg_import_partner_limit)

		active_ids = self.search(cr, uid, [('is_imported','=', False)], limit=int(arg_import_partner_limit), context=context)
		if active_ids:
			self.actual_import(cr, uid, active_ids, context=context)
		else:
			print "no partner to import"
		return True

	################################################################
	# the import process
	################################################################
	def actual_import(self, cr, uid, ids, context=None):
		i = 0
		ex = 0

		partner = self.pool.get('res.partner')

		for import_arg in self.browse(cr, uid, ids, context=context):

			cust_data = {}
			country_id = False
			if not import_arg.cust_country_name:
				self.write(cr, uid, [import_arg.id], {'notes':'NO COUNTRY'}, context=context)
				ex = ex + 1
				cr.commit()
				continue

			for k in CUST_MAPPING.keys():
				partner_fname = CUST_MAPPING[k]

				import_ls_fname = "import_arg.%s" % k 
				cust_data.update( {partner_fname : eval(import_ls_fname)})

				# import pdb; pdb.set_trace()

				if k == 'cust_province':

					country_id = self.find_or_create_country(cr, uid, import_arg.cust_country_name, context=context)
					cust_data.update({'country_id': country_id})
			
					state_id = self.find_or_create_state(cr, uid, import_arg.cust_province,country_id, context=context)
					cust_data.update({'state_id': state_id})
				
				if k == 'cust_country_name':
					if not country_id:
						country_id = self.find_or_create_country(cr, uid, import_arg.cust_country_name)
					cust_data.update({'country_id': country_id})



			print cust_data
			cust_data.update({'comment': 'ARG'})
			
			########################## check exiting partner partner 
			pid = partner.search(cr, uid, [('nomor_polis','=',import_arg.policy_no)],context=context)
			if not pid:
				pid = partner.create(cr, uid, cust_data, context=context)	
				i = i + 1
			else:
				pid = pid[0]
				_logger.warning('Partner exist with nomor_polis %s' % import_arg.policy_no)
				ex = ex + 1


			#commit per record
			cr.execute("update reliance_import_arg set is_imported='t' where id=%s" % import_arg.id)
			cr.commit()

		raise osv.except_osv( 'OK!' , 'Done creating %s partner and skipped %s existing' % (i, ex) )


class import_arg_polis_risk(osv.osv): 
	_name = "reliance.import_arg_polis_risk"
	_columns = {
		"policy_no"					:	fields.char("POLICY_NO"),
		"asset_description"			:	fields.char("ASSET_DESCRIPTION"),
		"total_premi"				:	fields.char("TOTAL_PREMI"),
		"total_nilai_pertanggungan"	:	fields.char("TOTAL_NILAI_PERTANGGUNGAN"),
		'is_imported' 		: 	fields.boolean("Imported to Polis Risk?", select=1),
		"notes"				:	fields.char("Notes"),
	}


	def action_import(self, cr, uid, context=None):
		active_ids = context and context.get('active_ids', False)
		if not context:
			context = {}

		self.actual_import(cr, uid, active_ids, context=context)


	def cron_import(self, cr, uid, context=None):
		arg_import_polis_risk_limit = self.pool.get('ir.config_parameter').get_param(cr, uid, 'arg_import_polis_risk_limit')
		_logger.warning('running cron import_arg_polis_risk, limit=%s' % arg_import_polis_risk_limit)

		active_ids = self.search(cr, uid, [('is_imported','=', False)], limit=int(arg_import_polis_risk_limit), context=context)
		if active_ids:
			self.actual_import(cr, uid, active_ids, context=context)
		else:
			print "no partner to import"
		return True

	################################################################
	# the import process
	################################################################
	def actual_import(self, cr, uid, ids, context=None):
		i = 0
		ex = 0

		partner = self.pool.get('res.partner')

		for import_arg in self.browse(cr, uid, ids, context=context):	

			#commit per record
			i = 1 +1
			cr.execute("update reliance_import_arg set is_imported='t' where id=%s" % import_arg.id)
			cr.commit()

		raise osv.except_osv( 'OK!' , 'Done creating %s partner and skipped %s' % (i, ex) )
