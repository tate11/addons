# -*- coding: utf-8 -*-
import base64

from openerp import SUPERUSER_ID
from openerp import http
from openerp.tools.translate import _
from openerp.http import request

from openerp.addons.website.models.website import slug

class website_hr_recruitment(http.Controller):
    @http.route([
        '/jobs',
        '/jobs/country/<model("res.country"):country>',
        '/jobs/department/<model("hr.department"):department>',
        '/jobs/country/<model("res.country"):country>/department/<model("hr.department"):department>',
        '/jobs/office/<int:office_id>',
        '/jobs/country/<model("res.country"):country>/office/<int:office_id>',
        '/jobs/department/<model("hr.department"):department>/office/<int:office_id>',
        '/jobs/country/<model("res.country"):country>/department/<model("hr.department"):department>/office/<int:office_id>',
    ], type='http', auth="public", website=True)
    def jobs(self, country=None, department=None, office_id=None, **kwargs):
        env = request.env(context=dict(request.env.context, show_address=True, no_tag_br=True))

        Country = env['res.country']
        Jobs = env['hr.job']

        # List jobs available to current UID
        job_ids = Jobs.search([('website_published','=',True)], order="website_published desc,no_of_recruitment desc").ids

        # Browse jobs as superuser, because address is restricted
        jobs = Jobs.sudo().browse(job_ids)

        # Deduce departments and offices of those jobs
        departments = set(j.department_id for j in jobs if j.department_id)
        offices = set(j.address_id for j in jobs if j.address_id)
        countries = set(o.country_id for o in offices if o.country_id)

        # Default search by user country
        if not (country or department or office_id or kwargs.get('all_countries')):
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                countries_ = Country.search([('code', '=', country_code)])
                country = countries_[0] if countries_ else None
                if not any(j for j in jobs if j.address_id and j.address_id.country_id == country):
                    country = False

        # Filter the matching one
        if country and not kwargs.get('all_countries'):
            jobs = (j for j in jobs if j.address_id is None or j.address_id.country_id and j.address_id.country_id.id == country.id)
        if department:
            jobs = (j for j in jobs if j.department_id and j.department_id.id == department.id)
        if office_id:
            jobs = (j for j in jobs if j.address_id and j.address_id.id == office_id)

        # Render page
        return request.website.render("website_hr_recruitment.index", {
            'jobs': jobs,
            'countries': countries,
            'departments': departments,
            'offices': offices,
            'country_id': country,
            'department_id': department,
            'office_id': office_id,
        })

    @http.route('/jobs/add', type='http', auth="user", website=True)
    def jobs_add(self, **kwargs):
        job = request.env['hr.job'].create({
            'name': _('New Job Offer'),
        })
        return request.redirect("/jobs/detail/%s?enable_editor=1" % slug(job))

    @http.route('/jobs/detail/<model("hr.job"):job>', type='http', auth="public", website=True)
    def jobs_detail(self, job, **kwargs):
        return request.render("website_hr_recruitment.detail", {
            'job': job,
            'main_object': job,
        })

    @http.route('/jobs/apply/<model("hr.job"):job>', type='http', auth="user", website=True)
    def jobs_apply(self, job, **kw):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry
        env = request.env(context=dict(request.env.context, show_address=True, no_tag_br=True))

        error = {}
        default = {}

        if 'website_hr_recruitment_error' in request.session:
            error = request.session.pop('website_hr_recruitment_error')
            default = request.session.pop('website_hr_recruitment_default')
        
        jenis_kelamins = [('L','Pria'),('W','Wanita')]
        statuss = [('single','Belum Kawin'),('married','Kawin'),('divorced','Janda/Duda')]
        ktp = [('KTP','Kartu Tanda Penduduk'),('passport','Passport')]
        # import pdb;pdb.set_trace()
        kota = env['hr_recruit.kota']
        kota_ids = kota.search([])

        agama = env['hr_recruit.agama']
        agama_ids = agama.search([])

        country = env['res.country']
        country_ids = country.search([])

        provinsi = env['hr_recruit.prov']
        provinsi_ids = provinsi.search([])

        kecamatan = env['hr_recruit.issued']
        kecamatan_ids = kecamatan.search([])

        types = env['hr.recruitment.degree']
        type_ids = types.search([])

        pt = env['hr_recruit.pt']
        pt_ids = pt.search([])

        jurusan = env['hr_recruit.jurusan_detail']
        jurusan_ids = jurusan.search([])

        #pengalaman kerja
        name_kerja = kw.get('name_kerja','')
        tempat_kerja = kw.get('tempat_kerja','')
        tahun_msk_kerja = kw.get('tahun_msk_kerja','')
        tahun_klr_kerja = kw.get('tahun_klr_kerja','')
        jabatan_kerja = kw.get('jabatan_kerja','')
        gaji_kerja = kw.get('gaji_kerja','')
        alasan_kerja = kw.get('alasan_kerja','')

        riwayat_kerja = [(0,0,{'name'     : name_kerja,
                             'tempat'   : tempat_kerja,
                             'tahun_msk': tahun_msk_kerja,
                             'tahun_klr': tahun_klr_kerja,
                             'jabatan'  : jabatan_kerja,
                             'gaji'     : gaji_kerja,
                             'alasan'   : alasan_kerja
                             })]

        return request.render("website_hr_recruitment.apply", {
            'job': job,
            'error': error,
            'default': default,
            'jenis_kelamins': jenis_kelamins,
            'kota_ids' : kota_ids,
            'agama_ids' : agama_ids,
            'country_ids' : country_ids,
            'kecamatan_ids' : kecamatan_ids, 
            'provinsi_ids' : provinsi_ids,
            'statuss' : statuss,
            'type_ids' : type_ids,
            'pt_ids' : pt_ids,
            'jurusan_ids' : jurusan_ids,
            'ktp' : ktp,
            'rwt_krj_ids' : riwayat_kerja,
        })

    def _get_applicant_char_fields(self):
        return ['email_from', 'partner_name','pengalaman', 'jenis_id', 'no_id', 'description', 'jen_kel', 'alamat1', 'telp1', 'tgl_lahir', 'kode1', 'status']

    def _get_applicant_relational_fields(self):
        return ['department_id', 'jurusan_id', 'job_id', 'kota_id', 'agama_id', 'country_id1', 'country_id', 'prov_id', 'kec_id', 'pt_id', 'type_id']

    def _get_applicant_one2many_fields(self):
        return ['rwt_krj_ids']

    @http.route('/jobs/thankyou', methods=['POST'], type='http', auth="public", website=True)
    def jobs_thankyou(self, **post):
        error = {}
        for field_name in ["partner_name", "phone", "email_from"]:
            if not post.get(field_name):
                error[field_name] = 'missing'
        if error:
            request.session['website_hr_recruitment_error'] = error
            ufile = post.pop('ufile')
            if ufile:
                error['ufile'] = 'reset'
            request.session['website_hr_recruitment_default'] = post
            return request.redirect('/jobs/apply/%s' % post.get("job_id"))

        # public user can't create applicants (duh)
        env = request.env(user=SUPERUSER_ID)
        value = {
            'source_id' : env.ref('hr_recruitment.source_website_company').id,
            'name': '%s\'s Application' % post.get('partner_name'), 
        }
        for f in self._get_applicant_char_fields():
            value[f] = post.get(f)
        for f in self._get_applicant_relational_fields():
            value[f] = int(post.get(f) or 0)
        for f in self._get_applicant_one2many_fields():
            value[f] = post.get(f)
        
        # Retro-compatibility for saas-3. "phone" field should be replace by "partner_phone" in the template in trunk.
        value['partner_phone'] = post.pop('phone', False)

        applicant_id = env['hr.applicant'].create(value).id
        if post['ufile']:
            attachment_value = {
                'name': post['ufile'].filename,
                'res_name': value['partner_name'],
                'res_model': 'hr.applicant',
                'res_id': applicant_id,
                'datas': base64.encodestring(post['ufile'].read()),
                'datas_fname': post['ufile'].filename,
            }
            env['ir.attachment'].create(attachment_value)
        return request.render("website_hr_recruitment.thankyou", {})

# vim :et:
