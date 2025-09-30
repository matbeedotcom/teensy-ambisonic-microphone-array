#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <numpy/arrayobject.h>
#ifdef I
#undef I  // Undefine complex.h's I macro before including ODAS headers
#endif
#include <odas/odas.h>
#include <math.h>

// ============================================================================
// ODAS Pipeline Object - holds complete processing chain
// ============================================================================
typedef struct {
    PyObject_HEAD

    // Configuration
    unsigned int nChannels;
    unsigned int frameSize;
    unsigned int halfFrameSize;
    unsigned int sampleRate;

    // STFT Module
    mod_stft_obj * mod_stft;
    msg_hops_cfg * hops_cfg;
    msg_spectra_cfg * spectra_cfg;
    msg_hops_obj * hops_in;
    msg_spectra_obj * spectra_out;

    // SSL Module
    mod_ssl_obj * mod_ssl;
    mod_ssl_cfg * ssl_cfg;
    msg_pots_cfg * pots_cfg;
    msg_pots_obj * pots_out;

    // SST Module (optional)
    mod_sst_obj * mod_sst;
    mod_sst_cfg * sst_cfg;
    msg_targets_cfg * targets_cfg;
    msg_tracks_cfg * tracks_cfg;
    msg_targets_obj * targets_in;
    msg_tracks_obj * tracks_out;

    // SSS Module (optional - sound source separation)
    mod_sss_obj * mod_sss;
    mod_sss_cfg * sss_cfg;
    msg_powers_cfg * powers_cfg;
    msg_powers_obj * powers_in;
    msg_spectra_obj * separated_out;  // Separated audio spectra
    msg_spectra_obj * residual_out;   // Residual audio spectra

    // ISTFT Module (optional - for converting separated spectra back to time domain)
    mod_istft_obj * mod_istft_sep;
    mod_istft_obj * mod_istft_res;
    msg_hops_obj * hops_sep_out;  // Separated audio hops (time domain)
    msg_hops_obj * hops_res_out;  // Residual audio hops (time domain)

    // Microphone configuration
    mics_obj * mics;
    samplerate_obj * samplerate;
    soundspeed_obj * soundspeed;
    spatialfilters_obj * spatialfilters;

    char enabled;
    char enable_tracking;   // Enable SST module
    char enable_separation; // Enable SSS module

} PyOdasPipeline;

// ============================================================================
// Helper Functions
// ============================================================================

// Create microphone configuration from Python dict
static mics_obj* create_mics_from_dict(PyObject* mic_dict, unsigned int nChannels) {
    mics_obj * mics = mics_construct_zero(nChannels);

    // Extract microphone positions from dict
    for (unsigned int iChannel = 0; iChannel < nChannels; iChannel++) {
        char key[32];
        snprintf(key, sizeof(key), "mic_%u", iChannel);

        PyObject *mic_pos = PyDict_GetItemString(mic_dict, key);
        if (mic_pos && PyList_Check(mic_pos) && PyList_Size(mic_pos) == 3) {
            float x = (float)PyFloat_AsDouble(PyList_GetItem(mic_pos, 0));
            float y = (float)PyFloat_AsDouble(PyList_GetItem(mic_pos, 1));
            float z = (float)PyFloat_AsDouble(PyList_GetItem(mic_pos, 2));

            // Store actual position in mu array (positions in meters)
            mics->mu[iChannel * 3 + 0] = x;
            mics->mu[iChannel * 3 + 1] = y;
            mics->mu[iChannel * 3 + 2] = z;

            // Store normalized direction (unit vector pointing from origin to mic)
            float norm = sqrtf(x*x + y*y + z*z);
            if (norm > 0.0f) {
                mics->direction[iChannel * 3 + 0] = x / norm;
                mics->direction[iChannel * 3 + 1] = y / norm;
                mics->direction[iChannel * 3 + 2] = z / norm;
            } else {
                // Default to pointing up if at origin
                mics->direction[iChannel * 3 + 0] = 0.0f;
                mics->direction[iChannel * 3 + 1] = 0.0f;
                mics->direction[iChannel * 3 + 2] = 1.0f;
            }
        }
    }

    return mics;
}

// Convert pots to Python list of dicts
static PyObject* pots_to_python(const pots_obj* pots, unsigned int nPots) {
    PyObject* result = PyList_New(nPots);

    for (unsigned int iPot = 0; iPot < nPots; iPot++) {
        PyObject* pot_dict = PyDict_New();

        // Each pot has 4 values: x, y, z, value
        float x = pots->array[iPot * 4 + 0];
        float y = pots->array[iPot * 4 + 1];
        float z = pots->array[iPot * 4 + 2];
        float value = pots->array[iPot * 4 + 3];

        PyDict_SetItemString(pot_dict, "x", PyFloat_FromDouble(x));
        PyDict_SetItemString(pot_dict, "y", PyFloat_FromDouble(y));
        PyDict_SetItemString(pot_dict, "z", PyFloat_FromDouble(z));
        PyDict_SetItemString(pot_dict, "value", PyFloat_FromDouble(value));

        PyList_SetItem(result, iPot, pot_dict);
    }

    return result;
}

// Convert tracks to Python list of dicts
static PyObject* tracks_to_python(const tracks_obj* tracks) {
    PyObject* result = PyList_New(0);

    for (unsigned int iTrack = 0; iTrack < tracks->nTracks; iTrack++) {
        // Only include active tracks (with non-zero ID)
        if (tracks->ids[iTrack] != 0) {
            PyObject* track_dict = PyDict_New();

            // Track position: x, y, z
            float x = tracks->array[iTrack * 3 + 0];
            float y = tracks->array[iTrack * 3 + 1];
            float z = tracks->array[iTrack * 3 + 2];
            float activity = tracks->activity[iTrack];
            unsigned long long id = tracks->ids[iTrack];

            PyDict_SetItemString(track_dict, "id", PyLong_FromUnsignedLongLong(id));
            PyDict_SetItemString(track_dict, "x", PyFloat_FromDouble(x));
            PyDict_SetItemString(track_dict, "y", PyFloat_FromDouble(y));
            PyDict_SetItemString(track_dict, "z", PyFloat_FromDouble(z));
            PyDict_SetItemString(track_dict, "activity", PyFloat_FromDouble(activity));

            // Add tag if available
            if (tracks->tags && tracks->tags[iTrack]) {
                PyDict_SetItemString(track_dict, "tag", PyUnicode_FromString(tracks->tags[iTrack]));
            }

            PyList_Append(result, track_dict);
            Py_DECREF(track_dict);
        }
    }

    return result;
}

// Convert hops (time-domain audio) to NumPy array
static PyObject* hops_to_numpy(const hops_obj* hops, unsigned int nChannels, unsigned int hopSize) {
    npy_intp dims[2] = {hopSize, nChannels};
    PyObject* array = PyArray_SimpleNew(2, dims, NPY_FLOAT32);
    float* data = (float*)PyArray_DATA((PyArrayObject*)array);

    for (unsigned int iSample = 0; iSample < hopSize; iSample++) {
        for (unsigned int iChannel = 0; iChannel < nChannels; iChannel++) {
            data[iSample * nChannels + iChannel] = hops->array[iChannel][iSample];
        }
    }

    return array;
}

// ============================================================================
// PyOdasPipeline Methods
// ============================================================================

static void PyOdasPipeline_dealloc(PyOdasPipeline *self) {
    // Clean up ODAS modules
    if (self->mod_stft) mod_stft_destroy(self->mod_stft);
    if (self->mod_ssl) mod_ssl_destroy(self->mod_ssl);
    if (self->mod_sst) mod_sst_destroy(self->mod_sst);
    if (self->mod_sss) mod_sss_destroy(self->mod_sss);
    if (self->mod_istft_sep) mod_istft_destroy(self->mod_istft_sep);
    if (self->mod_istft_res) mod_istft_destroy(self->mod_istft_res);

    // Clean up configurations
    if (self->ssl_cfg) {
        if (self->ssl_cfg->levels) free(self->ssl_cfg->levels);
        if (self->ssl_cfg->deltas) free(self->ssl_cfg->deltas);
        free(self->ssl_cfg);
    }
    if (self->sst_cfg) mod_sst_cfg_destroy(self->sst_cfg);
    if (self->sss_cfg) mod_sss_cfg_destroy(self->sss_cfg);
    if (self->hops_cfg) free(self->hops_cfg);
    if (self->spectra_cfg) free(self->spectra_cfg);
    if (self->pots_cfg) free(self->pots_cfg);
    if (self->targets_cfg) free(self->targets_cfg);
    if (self->tracks_cfg) free(self->tracks_cfg);
    if (self->powers_cfg) free(self->powers_cfg);

    // Clean up messages
    if (self->hops_in) {
        if (self->hops_in->hops) hops_destroy(self->hops_in->hops);
        free(self->hops_in);
    }
    if (self->spectra_out) msg_spectra_destroy(self->spectra_out);
    if (self->pots_out) msg_pots_destroy(self->pots_out);
    if (self->targets_in) msg_targets_destroy(self->targets_in);
    if (self->tracks_out) msg_tracks_destroy(self->tracks_out);
    if (self->powers_in) msg_powers_destroy(self->powers_in);
    if (self->separated_out) msg_spectra_destroy(self->separated_out);
    if (self->residual_out) msg_spectra_destroy(self->residual_out);
    if (self->hops_sep_out) {
        if (self->hops_sep_out->hops) hops_destroy(self->hops_sep_out->hops);
        free(self->hops_sep_out);
    }
    if (self->hops_res_out) {
        if (self->hops_res_out->hops) hops_destroy(self->hops_res_out->hops);
        free(self->hops_res_out);
    }

    // Clean up mic/config objects
    if (self->mics) mics_destroy(self->mics);
    if (self->samplerate) free(self->samplerate);
    if (self->soundspeed) free(self->soundspeed);
    if (self->spatialfilters) spatialfilters_destroy(self->spatialfilters);

    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject* PyOdasPipeline_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    PyOdasPipeline *self;
    self = (PyOdasPipeline *)type->tp_alloc(type, 0);
    if (self != NULL) {
        self->nChannels = 0;
        self->frameSize = 0;
        self->halfFrameSize = 0;
        self->sampleRate = 0;
        self->mod_stft = NULL;
        self->mod_ssl = NULL;
        self->mod_sst = NULL;
        self->mod_sss = NULL;
        self->mod_istft_sep = NULL;
        self->mod_istft_res = NULL;
        self->ssl_cfg = NULL;
        self->sst_cfg = NULL;
        self->sss_cfg = NULL;
        self->hops_cfg = NULL;
        self->spectra_cfg = NULL;
        self->pots_cfg = NULL;
        self->targets_cfg = NULL;
        self->tracks_cfg = NULL;
        self->powers_cfg = NULL;
        self->hops_in = NULL;
        self->spectra_out = NULL;
        self->pots_out = NULL;
        self->targets_in = NULL;
        self->tracks_out = NULL;
        self->powers_in = NULL;
        self->separated_out = NULL;
        self->residual_out = NULL;
        self->hops_sep_out = NULL;
        self->hops_res_out = NULL;
        self->mics = NULL;
        self->samplerate = NULL;
        self->soundspeed = NULL;
        self->spatialfilters = NULL;
        self->enabled = 1;
        self->enable_tracking = 0;
        self->enable_separation = 0;
    }
    return (PyObject *)self;
}

static int PyOdasPipeline_init(PyOdasPipeline *self, PyObject *args, PyObject *kwds) {
    PyObject *config_dict;

    if (!PyArg_ParseTuple(args, "O", &config_dict)) {
        return -1;
    }

    if (!PyDict_Check(config_dict)) {
        PyErr_SetString(PyExc_TypeError, "Configuration must be a dictionary");
        return -1;
    }

    // Extract basic configuration
    PyObject *py_nChannels = PyDict_GetItemString(config_dict, "n_channels");
    PyObject *py_frameSize = PyDict_GetItemString(config_dict, "frame_size");
    PyObject *py_sampleRate = PyDict_GetItemString(config_dict, "sample_rate");
    PyObject *py_mics = PyDict_GetItemString(config_dict, "mics");

    if (!py_nChannels || !py_frameSize || !py_sampleRate || !py_mics) {
        PyErr_SetString(PyExc_ValueError, "Missing required config: n_channels, frame_size, sample_rate, mics");
        return -1;
    }

    self->nChannels = (unsigned int)PyLong_AsLong(py_nChannels);
    self->frameSize = (unsigned int)PyLong_AsLong(py_frameSize);
    self->sampleRate = (unsigned int)PyLong_AsLong(py_sampleRate);

    // IMPORTANT: ODAS STFT uses overlap-add with 50% overlap
    // So STFT frameSize = 2 * hopSize
    // If user passes frame_size=512, that's the hopSize, and STFT frameSize=1024
    unsigned int hopSize = self->frameSize;
    unsigned int stftFrameSize = hopSize * 2;  // 2x for 50% overlap
    self->halfFrameSize = stftFrameSize / 2 + 1;

    // Create microphone configuration
    self->mics = create_mics_from_dict(py_mics, self->nChannels);

    // Create samplerate object
    self->samplerate = (samplerate_obj *)malloc(sizeof(samplerate_obj));
    self->samplerate->mu = (float)self->sampleRate;
    self->samplerate->sigma2 = 0.01f;

    // Create soundspeed object (343 m/s at 20°C)
    self->soundspeed = (soundspeed_obj *)malloc(sizeof(soundspeed_obj));
    self->soundspeed->mu = 343.0f;
    self->soundspeed->sigma2 = 0.1f;

    // Create empty spatial filters (not used for basic SSL)
    self->spatialfilters = spatialfilters_construct_zero(0);

    // Configure hops (input time-domain audio)
    self->hops_cfg = (msg_hops_cfg *)malloc(sizeof(msg_hops_cfg));
    self->hops_cfg->hopSize = hopSize;  // Input hop size (e.g., 512)
    self->hops_cfg->nChannels = self->nChannels;
    self->hops_cfg->fS = self->sampleRate;

    // Configure spectra (STFT output)
    self->spectra_cfg = (msg_spectra_cfg *)malloc(sizeof(msg_spectra_cfg));
    self->spectra_cfg->halfFrameSize = self->halfFrameSize;
    self->spectra_cfg->nChannels = self->nChannels;
    self->spectra_cfg->fS = self->sampleRate;

    // Configure pots (SSL output)
    self->pots_cfg = (msg_pots_cfg *)malloc(sizeof(msg_pots_cfg));
    self->pots_cfg->nPots = 4;  // Max sources to detect
    self->pots_cfg->fS = self->sampleRate;

    // Create message objects
    self->hops_in = (msg_hops_obj *)malloc(sizeof(msg_hops_obj));
    self->hops_in->hops = hops_construct_zero(self->nChannels, self->hops_cfg->hopSize);
    self->hops_in->timeStamp = 0;
    self->hops_in->fS = self->sampleRate;

    self->spectra_out = msg_spectra_construct(self->spectra_cfg);
    self->pots_out = msg_pots_construct(self->pots_cfg);

    // Create STFT module
    mod_stft_cfg * stft_cfg = mod_stft_cfg_construct();
    self->mod_stft = mod_stft_construct(stft_cfg, self->hops_cfg, self->spectra_cfg);
    mod_stft_cfg_destroy(stft_cfg);
    mod_stft_enable(self->mod_stft);

    // Configure SSL module (matching tetrahedral_4ch-b.cfg)
    self->ssl_cfg = (mod_ssl_cfg *)malloc(sizeof(mod_ssl_cfg));
    self->ssl_cfg->mics = self->mics;
    self->ssl_cfg->samplerate = self->samplerate;
    self->ssl_cfg->soundspeed = self->soundspeed;
    self->ssl_cfg->spatialfilters = self->spatialfilters;
    self->ssl_cfg->interpRate = 4;
    self->ssl_cfg->epsilon = 1e-12f;  // Match config
    self->ssl_cfg->nLevels = 2;  // Two scanning levels
    self->ssl_cfg->levels = (unsigned int *)malloc(2 * sizeof(unsigned int));
    self->ssl_cfg->levels[0] = 2;
    self->ssl_cfg->levels[1] = 4;
    self->ssl_cfg->deltas = (signed int *)malloc(2 * sizeof(signed int));
    self->ssl_cfg->deltas[0] = -1;
    self->ssl_cfg->deltas[1] = -1;
    self->ssl_cfg->nMatches = 10;  // Match config
    self->ssl_cfg->probMin = 0.3f;  // Match config (reduced from 0.5)
    self->ssl_cfg->nRefinedLevels = 2;  // Match config
    self->ssl_cfg->nThetas = 360;
    self->ssl_cfg->gainMin = 0.25f;

    // Create SSL module
    self->mod_ssl = mod_ssl_construct(self->ssl_cfg, self->spectra_cfg, self->pots_cfg);
    mod_ssl_enable(self->mod_ssl);

    // Check if tracking is enabled
    PyObject *py_enable_tracking = PyDict_GetItemString(config_dict, "enable_tracking");
    if (py_enable_tracking && PyObject_IsTrue(py_enable_tracking)) {
        self->enable_tracking = 1;

        // Configure targets (input to SST - can be empty for auto-init)
        self->targets_cfg = msg_targets_cfg_construct();
        self->targets_cfg->nTargets = 0;  // No external targets
        self->targets_cfg->fS = self->sampleRate;

        // Configure tracks (output from SST)
        self->tracks_cfg = msg_tracks_cfg_construct();
        self->tracks_cfg->nTracks = 4;  // Max simultaneous tracks
        self->tracks_cfg->fS = self->sampleRate;

        // Create message objects
        self->targets_in = msg_targets_construct(self->targets_cfg);
        self->tracks_out = msg_tracks_construct(self->tracks_cfg);

        // Configure SST module
        self->sst_cfg = mod_sst_cfg_construct();
        self->sst_cfg->nTracksMax = 4;
        self->sst_cfg->hopSize = self->hops_cfg->hopSize;
        self->sst_cfg->mode = 'p';  // particle filter mode
        self->sst_cfg->add = 'p';   // passive add mode

        // Tracking parameters (particle filter)
        self->sst_cfg->sigmaQ = 0.001f;
        self->sst_cfg->nParticles = 1000;
        self->sst_cfg->st_alpha = 2.0f;
        self->sst_cfg->st_beta = 0.04f;
        self->sst_cfg->st_ratio = 0.5f;
        self->sst_cfg->ve_alpha = 0.05f;
        self->sst_cfg->ve_beta = 0.2f;
        self->sst_cfg->ve_ratio = 0.3f;
        self->sst_cfg->ac_alpha = 0.5f;
        self->sst_cfg->ac_beta = 0.2f;
        self->sst_cfg->ac_ratio = 0.2f;
        self->sst_cfg->Nmin = 0.7f;
        self->sst_cfg->epsilon = 1e-6f;
        // sigmaR values are standard deviations (sqrt of variance)
        self->sst_cfg->sigmaR_active = sqrtf(0.0225f);  // sqrt(sigmaR2_active)
        self->sst_cfg->sigmaR_prob = sqrtf(0.0025f);    // sqrt(sigmaR2_prob)
        self->sst_cfg->sigmaR_target = sqrtf(0.0025f);  // sqrt(sigmaR2_target)

        // Create GMM for active/inactive classification
        // Based on ODAS default configuration (respeaker.cfg)
        // Active GMM: mu=0.3, sigma=sqrt(0.0025)=0.05, weight=1.0
        self->sst_cfg->active_gmm = gaussians_1d_construct_null(1);
        self->sst_cfg->active_gmm->array[0] = gaussian_1d_construct_weightmusigma(1.0f, 0.3f, 0.05f);

        // Inactive GMM: mu=0.15, sigma=sqrt(0.0025)=0.05, weight=1.0
        self->sst_cfg->inactive_gmm = gaussians_1d_construct_null(1);
        self->sst_cfg->inactive_gmm->array[0] = gaussian_1d_construct_weightmusigma(1.0f, 0.15f, 0.05f);

        self->sst_cfg->Pfalse = 0.1f;
        self->sst_cfg->Pnew = 0.1f;
        self->sst_cfg->Ptrack = 0.8f;
        self->sst_cfg->theta_new = 0.9f;
        self->sst_cfg->N_prob = 5;
        self->sst_cfg->theta_prob = 0.8f;
        self->sst_cfg->theta_inactive = 0.9f;

        // Allocate N_inactive array (one entry per track)
        self->sst_cfg->N_inactive = (unsigned int *)malloc(self->sst_cfg->nTracksMax * sizeof(unsigned int));
        for (unsigned int i = 0; i < self->sst_cfg->nTracksMax; i++) {
            self->sst_cfg->N_inactive[i] = 150 + (i * 50);  // 150, 200, 250, 300 for 4 tracks
        }

        // Create SST module
        self->mod_sst = mod_sst_construct(self->sst_cfg, self->ssl_cfg, self->pots_cfg,
                                          self->targets_cfg, self->tracks_cfg);
        mod_sst_enable(self->mod_sst);
    }

    // Check if sound source separation is enabled
    PyObject *py_enable_separation = PyDict_GetItemString(config_dict, "enable_separation");
    if (py_enable_separation && PyObject_IsTrue(py_enable_separation)) {
        self->enable_separation = 1;

        // SSS requires tracking to be enabled
        if (!self->enable_tracking) {
            PyErr_SetString(PyExc_ValueError, "Sound source separation requires tracking to be enabled (enable_tracking=True)");
            return -1;
        }

        // Configure powers (input to SSS - audio power estimates)
        self->powers_cfg = (msg_powers_cfg *)malloc(sizeof(msg_powers_cfg));
        self->powers_cfg->halfFrameSize = self->halfFrameSize;
        self->powers_cfg->nChannels = self->nChannels;
        self->powers_cfg->fS = self->sampleRate;

        // Create message objects for separated audio
        self->powers_in = msg_powers_construct(self->powers_cfg);
        self->separated_out = msg_spectra_construct(self->spectra_cfg);
        self->residual_out = msg_spectra_construct(self->spectra_cfg);

        // Configure SSS module (matching tetrahedral_4ch-b.cfg)
        self->sss_cfg = mod_sss_cfg_construct();
        self->sss_cfg->mode_sep = 'g';  // Geometric Source Separation (DGSS) - better for small arrays
        self->sss_cfg->mode_pf = 'm';   // Multi-channel spectral subtraction post-filtering
        self->sss_cfg->nThetas = 360;   // Match SSL nThetas
        self->sss_cfg->gainMin = 0.25f; // Match SSL gainMin
        self->sss_cfg->epsilon = 1e-12f; // Match SSL epsilon
        self->sss_cfg->mics = self->mics;
        self->sss_cfg->samplerate = self->samplerate;
        self->sss_cfg->soundspeed = self->soundspeed;

        // DGSS parameters (Geometric Source Separation)
        self->sss_cfg->sep_gss_lambda = 0.5f;  // Match config
        self->sss_cfg->sep_gss_mu = 0.01f;     // Match config

        // Multi-channel spectral subtraction parameters (matching config)
        self->sss_cfg->pf_ms_bSize = 128;
        self->sss_cfg->pf_ms_alphaS = 0.8f;
        self->sss_cfg->pf_ms_L = 150;
        self->sss_cfg->pf_ms_delta = 5.0f;
        self->sss_cfg->pf_ms_alphaD = 0.85f;
        self->sss_cfg->pf_ms_eta = 0.3f;           // Match config (was 0.5)
        self->sss_cfg->pf_ms_alphaZ = 0.9f;        // Match config (was 0.95)
        self->sss_cfg->pf_ms_alphaPmin = 0.15f;    // Match config (was 0.9)
        self->sss_cfg->pf_ms_thetaWin = 0.7f;      // Match config (was 0.3)
        self->sss_cfg->pf_ms_alphaWin = 0.7f;      // Match config (was 0.3)
        self->sss_cfg->pf_ms_maxAbsenceProb = 0.7f; // Match config (was 0.9999)
        self->sss_cfg->pf_ms_Gmin = 0.1f;          // Match config (was 0.01)
        self->sss_cfg->pf_ms_winSizeLocal = 7;     // Match config (was 3)
        self->sss_cfg->pf_ms_winSizeGlobal = 15;   // Match config (was 23)
        self->sss_cfg->pf_ms_winSizeFrame = 256;

        // Single-channel spectral subtraction parameters (matching config)
        self->sss_cfg->pf_ss_Gmin = 0.1f;   // Match config
        self->sss_cfg->pf_ss_Gmid = 0.7f;   // Match config (was 0.9)
        self->sss_cfg->pf_ss_Gslope = 3.0f; // Match config (was 10.0)

        // Create SSS module
        self->mod_sss = mod_sss_construct(self->sss_cfg, self->tracks_cfg, self->spectra_cfg);
        mod_sss_enable(self->mod_sss);

        // Configure ISTFT modules for converting separated spectra back to time domain
        mod_istft_cfg * istft_cfg = mod_istft_cfg_construct();

        // Create ISTFT for separated audio
        self->mod_istft_sep = mod_istft_construct(istft_cfg, self->spectra_cfg, self->hops_cfg);
        mod_istft_enable(self->mod_istft_sep);

        // Create ISTFT for residual audio
        self->mod_istft_res = mod_istft_construct(istft_cfg, self->spectra_cfg, self->hops_cfg);
        mod_istft_enable(self->mod_istft_res);

        mod_istft_cfg_destroy(istft_cfg);

        // Create output hops objects
        self->hops_sep_out = (msg_hops_obj *)malloc(sizeof(msg_hops_obj));
        self->hops_sep_out->hops = hops_construct_zero(self->nChannels, self->hops_cfg->hopSize);
        self->hops_sep_out->timeStamp = 0;
        self->hops_sep_out->fS = self->sampleRate;

        self->hops_res_out = (msg_hops_obj *)malloc(sizeof(msg_hops_obj));
        self->hops_res_out->hops = hops_construct_zero(self->nChannels, self->hops_cfg->hopSize);
        self->hops_res_out->timeStamp = 0;
        self->hops_res_out->fS = self->sampleRate;
    }

    return 0;
}

// Process audio frame through pipeline
static PyObject* PyOdasPipeline_process(PyOdasPipeline *self, PyObject *args) {
    PyArrayObject *audio_array;

    if (!PyArg_ParseTuple(args, "O!", &PyArray_Type, &audio_array)) {
        return NULL;
    }

    // Validate input shape: (hopSize, nChannels)
    if (PyArray_NDIM(audio_array) != 2) {
        PyErr_SetString(PyExc_ValueError, "Audio array must be 2D (samples, channels)");
        return NULL;
    }

    npy_intp *dims = PyArray_DIMS(audio_array);
    unsigned int nSamples = (unsigned int)dims[0];
    unsigned int nChannels = (unsigned int)dims[1];

    if (nChannels != self->nChannels) {
        PyErr_Format(PyExc_ValueError, "Expected %u channels, got %u", self->nChannels, nChannels);
        return NULL;
    }

    if (nSamples != self->hops_cfg->hopSize) {
        PyErr_Format(PyExc_ValueError, "Expected %u samples, got %u", self->hops_cfg->hopSize, nSamples);
        return NULL;
    }

    // Copy audio data to hops object
    float *audio_data = (float *)PyArray_DATA(audio_array);
    for (unsigned int iSample = 0; iSample < nSamples; iSample++) {
        for (unsigned int iChannel = 0; iChannel < nChannels; iChannel++) {
            self->hops_in->hops->array[iChannel][iSample] =
                audio_data[iSample * nChannels + iChannel];
        }
    }

    // CRITICAL: Increment timestamp - ODAS checks for timeStamp==0 to detect zero/invalid frames
    // Without this, mod_stft_process will return -1 and not process the audio!
    self->hops_in->timeStamp++;

    // Connect modules
    mod_stft_connect(self->mod_stft, self->hops_in, self->spectra_out);
    mod_ssl_connect(self->mod_ssl, self->spectra_out, self->pots_out);

    // Process STFT (return value indicates data availability, not error)
    mod_stft_process(self->mod_stft);

    // Process SSL (return value indicates data availability, not error)
    mod_ssl_process(self->mod_ssl);

    // Process SST if enabled
    if (self->enable_tracking) {
        // Synchronize targets timestamp with pots (SST requires in1->timeStamp == in2->timeStamp)
        self->targets_in->timeStamp = self->pots_out->timeStamp;

        mod_sst_connect(self->mod_sst, self->pots_out, self->targets_in, self->tracks_out);
        mod_sst_process(self->mod_sst);
        mod_sst_disconnect(self->mod_sst);

        // SST sets tracks_out->timeStamp = pots_out->timeStamp
        // which should equal spectra_out->timeStamp
    }

    // Process SSS if enabled (requires tracking)
    if (self->enable_separation && self->enable_tracking) {
        // Synchronize timestamps - SSS requires all inputs to have matching timestamps
        // spectra_out->timeStamp is set by STFT from hops_in->timeStamp
        // tracks_out->timeStamp is set by SST from pots_out->timeStamp
        // powers_in->timeStamp needs to match
        self->powers_in->timeStamp = self->spectra_out->timeStamp;

        // Connect SSS module
        // SSS takes: spectra (input audio), powers (unused for now), tracks (source positions)
        // SSS outputs: separated_out (beamformed audio), residual_out (remainder)
        mod_sss_connect(self->mod_sss, self->spectra_out, self->powers_in,
                       self->tracks_out, self->separated_out, self->residual_out);

        // Process SSS (beamforming/separation)
        mod_sss_process(self->mod_sss);

        // Convert separated spectra back to time domain using ISTFT
        mod_istft_connect(self->mod_istft_sep, self->separated_out, self->hops_sep_out);
        mod_istft_process(self->mod_istft_sep);
        mod_istft_disconnect(self->mod_istft_sep);

        mod_istft_connect(self->mod_istft_res, self->residual_out, self->hops_res_out);
        mod_istft_process(self->mod_istft_res);
        mod_istft_disconnect(self->mod_istft_res);

        mod_sss_disconnect(self->mod_sss);
    }

    // Disconnect modules
    mod_stft_disconnect(self->mod_stft);
    mod_ssl_disconnect(self->mod_ssl);

    // Convert pots to Python
    PyObject* pots_list = pots_to_python(self->pots_out->pots, self->pots_cfg->nPots);

    // Create result dict
    PyObject* result = PyDict_New();
    PyDict_SetItemString(result, "pots", pots_list);
    PyDict_SetItemString(result, "timestamp", PyLong_FromUnsignedLongLong(self->pots_out->timeStamp));

    // Add tracks if SST is enabled
    if (self->enable_tracking) {
        PyObject* tracks_list = tracks_to_python(self->tracks_out->tracks);
        PyDict_SetItemString(result, "tracks", tracks_list);
        Py_DECREF(tracks_list);
    }

    // Add separated audio if SSS is enabled
    if (self->enable_separation) {
        PyObject* separated_audio = hops_to_numpy(self->hops_sep_out->hops,
                                                   self->nChannels, self->hops_cfg->hopSize);
        PyObject* residual_audio = hops_to_numpy(self->hops_res_out->hops,
                                                  self->nChannels, self->hops_cfg->hopSize);
        PyDict_SetItemString(result, "separated", separated_audio);
        PyDict_SetItemString(result, "residual", residual_audio);
        Py_DECREF(separated_audio);
        Py_DECREF(residual_audio);
    }

    Py_DECREF(pots_list);

    return result;
}

// ============================================================================
// Python Type Definition
// ============================================================================

static PyMethodDef PyOdasPipeline_methods[] = {
    {"process", (PyCFunction)PyOdasPipeline_process, METH_VARARGS,
     "Process audio frame through ODAS pipeline"},
    {NULL}
};

static PyTypeObject PyOdasPipelineType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "_odas_core.OdasPipeline",
    .tp_doc = "ODAS processing pipeline",
    .tp_basicsize = sizeof(PyOdasPipeline),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = PyOdasPipeline_new,
    .tp_init = (initproc)PyOdasPipeline_init,
    .tp_dealloc = (destructor)PyOdasPipeline_dealloc,
    .tp_methods = PyOdasPipeline_methods,
};

// ============================================================================
// Legacy stub functions (for compatibility)
// ============================================================================

// SSL Module wrapper
static PyObject* create_ssl_module(PyObject *self, PyObject *args) {
    PyErr_SetString(PyExc_DeprecationWarning, "Use OdasPipeline instead");
    Py_RETURN_NONE;
}

// SST Module wrapper
static PyObject* create_sst_module(PyObject *self, PyObject *args) {
    PyErr_SetString(PyExc_DeprecationWarning, "Use OdasPipeline instead");
    Py_RETURN_NONE;
}

// SSS Module wrapper
static PyObject* create_sss_module(PyObject *self, PyObject *args) {
    PyErr_SetString(PyExc_DeprecationWarning, "Use OdasPipeline instead");
    Py_RETURN_NONE;
}

// Process audio frame
static PyObject* process_frame(PyObject *self, PyObject *args) {
    PyErr_SetString(PyExc_DeprecationWarning, "Use OdasPipeline.process() instead");
    Py_RETURN_NONE;
}

// Module methods
static PyMethodDef module_methods[] = {
    {"create_ssl_module", create_ssl_module, METH_VARARGS, "Create SSL module (deprecated)"},
    {"create_sst_module", create_sst_module, METH_VARARGS, "Create SST module (deprecated)"},
    {"create_sss_module", create_sss_module, METH_VARARGS, "Create SSS module (deprecated)"},
    {"process_frame", process_frame, METH_VARARGS, "Process audio frame (deprecated)"},
    {NULL, NULL, 0, NULL}
};

// Module definition
static struct PyModuleDef odas_core_module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "_odas_core",
    .m_doc = "ODAS module wrappers for sound source localization",
    .m_size = -1,
    .m_methods = module_methods
};

// Module initialization
PyMODINIT_FUNC PyInit__odas_core(void) {
    PyObject *m;

    import_array();

    // Register OdasPipeline type
    if (PyType_Ready(&PyOdasPipelineType) < 0) {
        return NULL;
    }

    m = PyModule_Create(&odas_core_module);
    if (m == NULL) {
        return NULL;
    }

    Py_INCREF(&PyOdasPipelineType);
    if (PyModule_AddObject(m, "OdasPipeline", (PyObject *)&PyOdasPipelineType) < 0) {
        Py_DECREF(&PyOdasPipelineType);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}