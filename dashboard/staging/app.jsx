const { useState, useEffect, useCallback } = React;

// Configuration
const API_BASE = window.location.origin;
const STORAGE_KEY = "staging-auth";

// ==================== UTILITY FUNCTIONS ====================

const loadAuth = () => {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch (err) {
        return null;
    }
};

const saveAuth = (auth) => {
    if (auth) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(auth));
    } else {
        localStorage.removeItem(STORAGE_KEY);
    }
};

const apiCall = async (auth, endpoint, options = {}) => {
    const headers = new Headers(options.headers || {});
    if (!(options.body instanceof FormData)) {
        headers.set("Content-Type", "application/json");
    }
    // Handle both accessToken and access_token
    const token = auth?.accessToken || auth?.access_token;
    if (token) {
        headers.set("Authorization", `Bearer ${token}`);
    }
    const response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    if (response.status === 204) return {};
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.detail || data.message || "Request failed");
    }
    return data;
};

const formatDate = (dateString) => {
    if (!dateString) return "—";
    return new Date(dateString).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
    });
};

const formatCurrency = (cents) => {
    return `$${(cents / 100).toFixed(2)}`;
};

// ==================== LOGIN COMPONENT ====================

const Login = ({ onLogin }) => {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");
        setLoading(true);
        try {
            const response = await fetch(`${API_BASE}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password }),
            });
            const data = await response.json();
            if (response.ok) {
                // Normalize the response format
                const authData = {
                    ...data,
                    accessToken: data.accessToken || data.access_token,
                };
                saveAuth(authData);
                onLogin(authData);
            } else {
                setError(data.detail || "Login failed");
            }
        } catch (err) {
            setError(err.message || "Network error. Please check your connection.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen gradient-bg flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-md w-full space-y-8 bg-white p-10 rounded-2xl shadow-2xl">
                <div className="text-center">
                    <h1 className="text-4xl font-bold text-gray-900 mb-2">
                        <i className="fas fa-home mr-2 text-purple-600"></i>
                        Virtual Staging
                    </h1>
                    <p className="text-gray-600 mt-2">Professional Property Staging Platform</p>
                </div>
                <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                <i className="fas fa-envelope mr-2 text-gray-400"></i>
                                Email Address
                            </label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="appearance-none relative block w-full px-4 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                placeholder="you@example.com"
                                required
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                <i className="fas fa-lock mr-2 text-gray-400"></i>
                                Password
                            </label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="appearance-none relative block w-full px-4 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                placeholder="Enter your password"
                                required
                            />
                        </div>
                    </div>

                    {error && (
                        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center">
                            <i className="fas fa-exclamation-circle mr-2"></i>
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        {loading ? (
                            <>
                                <i className="fas fa-spinner fa-spin mr-2"></i>
                                Logging in...
                            </>
                        ) : (
                            <>
                                <i className="fas fa-sign-in-alt mr-2"></i>
                                Sign In
                            </>
                        )}
                    </button>
                </form>
                <div className="text-center text-sm text-gray-600">
                    <p>Need help? Contact support</p>
                </div>
            </div>
        </div>
    );
};

// ==================== DASHBOARD COMPONENT ====================

const Dashboard = ({ auth, onLogout }) => {
    const [view, setView] = useState("overview");
    const [jobs, setJobs] = useState([]);
    const [properties, setProperties] = useState([]);
    const [packages, setPackages] = useState([]);
    const [analytics, setAnalytics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [showCreateProperty, setShowCreateProperty] = useState(false);
    const [showCreateJob, setShowCreateJob] = useState(false);

    const userRole = auth?.user?.role || "client";

    useEffect(() => {
        loadInitialData();
    }, []);

    useEffect(() => {
        if (view !== "overview") {
            loadViewData();
        }
    }, [view]);

    const loadInitialData = async () => {
        setLoading(true);
        try {
            await Promise.all([
                loadJobs(),
                loadProperties(),
                loadPackages(),
                userRole === "admin" || userRole === "manager" ? loadAnalytics() : Promise.resolve(),
            ]);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const loadViewData = async () => {
        try {
            if (view === "jobs") {
                await loadJobs();
            } else if (view === "properties") {
                await loadProperties();
            } else if (view === "admin" && (userRole === "admin" || userRole === "manager")) {
                await loadAnalytics();
            }
        } catch (err) {
            setError(err.message);
        }
    };

    const loadJobs = async () => {
        try {
            const data = await apiCall(auth, "/api/staging/jobs");
            setJobs(data || []);
        } catch (err) {
            console.error("Failed to load jobs:", err);
            setJobs([]);
        }
    };

    const loadProperties = async () => {
        try {
            const data = await apiCall(auth, "/api/staging/properties");
            setProperties(data || []);
        } catch (err) {
            console.error("Failed to load properties:", err);
            setProperties([]);
        }
    };

    const loadPackages = async () => {
        try {
            const data = await apiCall(auth, "/api/staging/packages");
            setPackages(data || []);
        } catch (err) {
            console.error("Failed to load packages:", err);
            setPackages([]);
        }
    };

    const loadAnalytics = async () => {
        try {
            const data = await apiCall(auth, "/api/staging/admin/analytics");
            setAnalytics(data);
        } catch (err) {
            console.error("Failed to load analytics:", err);
        }
    };

    const getStatusBadge = (status) => {
        const statusMap = {
            scheduled: { class: "status-scheduled", icon: "fa-calendar", label: "Scheduled" },
            in_progress: { class: "status-in_progress", icon: "fa-spinner", label: "In Progress" },
            photos_staged: { class: "status-photos_staged", icon: "fa-images", label: "Photos Ready" },
            completed: { class: "status-completed", icon: "fa-check-circle", label: "Completed" },
            cancelled: { class: "status-cancelled", icon: "fa-times-circle", label: "Cancelled" },
        };
        const statusInfo = statusMap[status] || { class: "bg-gray-100 text-gray-800", icon: "fa-circle", label: status };
        return (
            <span className={`status-badge ${statusInfo.class}`}>
                <i className={`fas ${statusInfo.icon} mr-1`}></i>
                {statusInfo.label}
            </span>
        );
    };

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Navigation Bar */}
            <nav className="bg-white shadow-lg border-b border-gray-200">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between h-16">
                        <div className="flex">
                            <div className="flex-shrink-0 flex items-center">
                                <h1 className="text-2xl font-bold text-purple-600">
                                    <i className="fas fa-home mr-2"></i>
                                    Virtual Staging
                                </h1>
                            </div>
                            <div className="hidden sm:ml-8 sm:flex sm:space-x-1">
                                <button
                                    onClick={() => setView("overview")}
                                    className={`inline-flex items-center px-4 py-2 border-b-2 text-sm font-medium transition-colors ${
                                        view === "overview"
                                            ? "border-purple-500 text-purple-600"
                                            : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                                    }`}
                                >
                                    <i className="fas fa-tachometer-alt mr-2"></i>
                                    Overview
                                </button>
                                <button
                                    onClick={() => setView("jobs")}
                                    className={`inline-flex items-center px-4 py-2 border-b-2 text-sm font-medium transition-colors ${
                                        view === "jobs"
                                            ? "border-purple-500 text-purple-600"
                                            : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                                    }`}
                                >
                                    <i className="fas fa-briefcase mr-2"></i>
                                    Jobs
                                    {jobs.length > 0 && (
                                        <span className="ml-2 bg-purple-100 text-purple-600 px-2 py-0.5 rounded-full text-xs">
                                            {jobs.length}
                                        </span>
                                    )}
                                </button>
                                <button
                                    onClick={() => setView("properties")}
                                    className={`inline-flex items-center px-4 py-2 border-b-2 text-sm font-medium transition-colors ${
                                        view === "properties"
                                            ? "border-purple-500 text-purple-600"
                                            : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                                    }`}
                                >
                                    <i className="fas fa-building mr-2"></i>
                                    Properties
                                    {properties.length > 0 && (
                                        <span className="ml-2 bg-purple-100 text-purple-600 px-2 py-0.5 rounded-full text-xs">
                                            {properties.length}
                                        </span>
                                    )}
                                </button>
                                {(userRole === "admin" || userRole === "manager") && (
                                    <button
                                        onClick={() => setView("admin")}
                                        className={`inline-flex items-center px-4 py-2 border-b-2 text-sm font-medium transition-colors ${
                                            view === "admin"
                                                ? "border-purple-500 text-purple-600"
                                                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                                        }`}
                                    >
                                        <i className="fas fa-cog mr-2"></i>
                                        Admin
                                    </button>
                                )}
                            </div>
                        </div>
                        <div className="flex items-center space-x-4">
                            <div className="text-right">
                                <div className="text-sm font-medium text-gray-700">{auth?.user?.email}</div>
                                <div className="text-xs text-gray-500 capitalize">{userRole}</div>
                            </div>
                            <button
                                onClick={onLogout}
                                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-gray-700 bg-gray-100 hover:bg-gray-200 transition-colors"
                            >
                                <i className="fas fa-sign-out-alt mr-2"></i>
                                Logout
                            </button>
                        </div>
                    </div>
                </div>
            </nav>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
                {error && (
                    <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center">
                        <i className="fas fa-exclamation-circle mr-2"></i>
                        {error}
                    </div>
                )}

                {/* Overview Tab */}
                {view === "overview" && (
                    <div className="space-y-6">
                        <div className="flex justify-between items-center">
                            <h2 className="text-3xl font-bold text-gray-900">Dashboard Overview</h2>
                            <div className="flex space-x-3">
                                <button
                                    onClick={() => setShowCreateProperty(true)}
                                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-purple-600 hover:bg-purple-700 transition-colors"
                                >
                                    <i className="fas fa-plus mr-2"></i>
                                    New Property
                                </button>
                                <button
                                    onClick={() => setShowCreateJob(true)}
                                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-purple-600 hover:bg-purple-700 transition-colors"
                                >
                                    <i className="fas fa-plus mr-2"></i>
                                    New Job
                                </button>
                            </div>
                        </div>

                        {/* Stats Cards */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div className="bg-white rounded-lg shadow-md p-6 card-hover">
                                <div className="flex items-center">
                                    <div className="flex-shrink-0 bg-purple-100 rounded-lg p-3">
                                        <i className="fas fa-briefcase text-purple-600 text-2xl"></i>
                                    </div>
                                    <div className="ml-4">
                                        <p className="text-sm font-medium text-gray-500">Total Jobs</p>
                                        <p className="text-2xl font-bold text-gray-900">{jobs.length}</p>
                                    </div>
                                </div>
                            </div>
                            <div className="bg-white rounded-lg shadow-md p-6 card-hover">
                                <div className="flex items-center">
                                    <div className="flex-shrink-0 bg-blue-100 rounded-lg p-3">
                                        <i className="fas fa-building text-blue-600 text-2xl"></i>
                                    </div>
                                    <div className="ml-4">
                                        <p className="text-sm font-medium text-gray-500">Properties</p>
                                        <p className="text-2xl font-bold text-gray-900">{properties.length}</p>
                                    </div>
                                </div>
                            </div>
                            <div className="bg-white rounded-lg shadow-md p-6 card-hover">
                                <div className="flex items-center">
                                    <div className="flex-shrink-0 bg-green-100 rounded-lg p-3">
                                        <i className="fas fa-check-circle text-green-600 text-2xl"></i>
                                    </div>
                                    <div className="ml-4">
                                        <p className="text-sm font-medium text-gray-500">Completed</p>
                                        <p className="text-2xl font-bold text-gray-900">
                                            {jobs.filter((j) => j.status === "completed").length}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Recent Jobs */}
                        <div className="bg-white rounded-lg shadow-md overflow-hidden">
                            <div className="px-6 py-4 border-b border-gray-200">
                                <h3 className="text-lg font-semibold text-gray-900">
                                    <i className="fas fa-clock mr-2 text-purple-600"></i>
                                    Recent Jobs
                                </h3>
                            </div>
                            {loading ? (
                                <div className="p-8 text-center text-gray-500">
                                    <i className="fas fa-spinner fa-spin text-3xl mb-4"></i>
                                    <p>Loading...</p>
                                </div>
                            ) : jobs.length === 0 ? (
                                <div className="p-8 text-center text-gray-500">
                                    <i className="fas fa-inbox text-4xl mb-4"></i>
                                    <p>No jobs yet. Create your first job to get started!</p>
                                </div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="min-w-full divide-y divide-gray-200">
                                        <thead className="bg-gray-50">
                                            <tr>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Job ID
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Status
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Created
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Priority
                                                </th>
                                            </tr>
                                        </thead>
                                        <tbody className="bg-white divide-y divide-gray-200">
                                            {jobs.slice(0, 5).map((job) => (
                                                <tr key={job.job_id} className="hover:bg-gray-50">
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                                        {job.job_id.substring(0, 12)}...
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">{getStatusBadge(job.status)}</td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                        {formatDate(job.created_at)}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <span className="px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800 capitalize">
                                                            {job.priority || "normal"}
                                                        </span>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Jobs Tab */}
                {view === "jobs" && (
                    <div>
                        <div className="flex justify-between items-center mb-6">
                            <h2 className="text-3xl font-bold text-gray-900">
                                <i className="fas fa-briefcase mr-2 text-purple-600"></i>
                                Jobs
                            </h2>
                            <button
                                onClick={() => setShowCreateJob(true)}
                                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-purple-600 hover:bg-purple-700 transition-colors"
                            >
                                <i className="fas fa-plus mr-2"></i>
                                New Job
                            </button>
                        </div>
                        {loading ? (
                            <div className="bg-white rounded-lg shadow-md p-12 text-center">
                                <i className="fas fa-spinner fa-spin text-4xl text-purple-600 mb-4"></i>
                                <p className="text-gray-600">Loading jobs...</p>
                            </div>
                        ) : (
                            <div className="bg-white rounded-lg shadow-md overflow-hidden">
                                <div className="overflow-x-auto">
                                    <table className="min-w-full divide-y divide-gray-200">
                                        <thead className="bg-gray-50">
                                            <tr>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Job ID
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Status
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Scheduled
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Priority
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Created
                                                </th>
                                            </tr>
                                        </thead>
                                        <tbody className="bg-white divide-y divide-gray-200">
                                            {jobs.length === 0 ? (
                                                <tr>
                                                    <td colSpan="5" className="px-6 py-12 text-center text-gray-500">
                                                        <i className="fas fa-inbox text-4xl mb-4 block"></i>
                                                        No jobs found. Create your first job to get started!
                                                    </td>
                                                </tr>
                                            ) : (
                                                jobs.map((job) => (
                                                    <tr key={job.job_id} className="hover:bg-gray-50 cursor-pointer">
                                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-purple-600">
                                                            {job.job_id.substring(0, 12)}...
                                                        </td>
                                                        <td className="px-6 py-4 whitespace-nowrap">{getStatusBadge(job.status)}</td>
                                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                            {job.scheduled_date ? formatDate(job.scheduled_date) : "—"}
                                                        </td>
                                                        <td className="px-6 py-4 whitespace-nowrap">
                                                            <span className="px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800 capitalize">
                                                                {job.priority || "normal"}
                                                            </span>
                                                        </td>
                                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                            {formatDate(job.created_at)}
                                                        </td>
                                                    </tr>
                                                ))
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Properties Tab */}
                {view === "properties" && (
                    <div>
                        <div className="flex justify-between items-center mb-6">
                            <h2 className="text-3xl font-bold text-gray-900">
                                <i className="fas fa-building mr-2 text-purple-600"></i>
                                Properties
                            </h2>
                            <button
                                onClick={() => setShowCreateProperty(true)}
                                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-purple-600 hover:bg-purple-700 transition-colors"
                            >
                                <i className="fas fa-plus mr-2"></i>
                                New Property
                            </button>
                        </div>
                        {loading ? (
                            <div className="bg-white rounded-lg shadow-md p-12 text-center">
                                <i className="fas fa-spinner fa-spin text-4xl text-purple-600 mb-4"></i>
                                <p className="text-gray-600">Loading properties...</p>
                            </div>
                        ) : (
                            <div className="bg-white rounded-lg shadow-md overflow-hidden">
                                <div className="overflow-x-auto">
                                    <table className="min-w-full divide-y divide-gray-200">
                                        <thead className="bg-gray-50">
                                            <tr>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Address
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    City
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    State
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Status
                                                </th>
                                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                    Created
                                                </th>
                                            </tr>
                                        </thead>
                                        <tbody className="bg-white divide-y divide-gray-200">
                                            {properties.length === 0 ? (
                                                <tr>
                                                    <td colSpan="5" className="px-6 py-12 text-center text-gray-500">
                                                        <i className="fas fa-inbox text-4xl mb-4 block"></i>
                                                        No properties found. Add your first property!
                                                    </td>
                                                </tr>
                                            ) : (
                                                properties.map((property) => (
                                                    <tr key={property.property_id} className="hover:bg-gray-50 cursor-pointer">
                                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                                            <i className="fas fa-map-marker-alt mr-2 text-purple-600"></i>
                                                            {property.address}
                                                        </td>
                                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                            {property.city || "—"}
                                                        </td>
                                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                            {property.state || "—"}
                                                        </td>
                                                        <td className="px-6 py-4 whitespace-nowrap">
                                                            <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                                                                {property.status}
                                                            </span>
                                                        </td>
                                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                            {formatDate(property.created_at)}
                                                        </td>
                                                    </tr>
                                                ))
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Admin Tab */}
                {view === "admin" && (userRole === "admin" || userRole === "manager") && (
                    <div>
                        <h2 className="text-3xl font-bold text-gray-900 mb-6">
                            <i className="fas fa-cog mr-2 text-purple-600"></i>
                            Admin Dashboard
                        </h2>
                        {analytics ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                                <div className="bg-white rounded-lg shadow-md p-6">
                                    <div className="text-sm font-medium text-gray-500">Total Jobs</div>
                                    <div className="text-3xl font-bold text-gray-900 mt-2">{analytics.total_jobs}</div>
                                </div>
                                <div className="bg-white rounded-lg shadow-md p-6">
                                    <div className="text-sm font-medium text-gray-500">This Month</div>
                                    <div className="text-3xl font-bold text-gray-900 mt-2">{analytics.jobs_this_month}</div>
                                </div>
                                <div className="bg-white rounded-lg shadow-md p-6">
                                    <div className="text-sm font-medium text-gray-500">Total Revenue</div>
                                    <div className="text-3xl font-bold text-gray-900 mt-2">
                                        {formatCurrency(analytics.total_revenue_cents)}
                                    </div>
                                </div>
                                <div className="bg-white rounded-lg shadow-md p-6">
                                    <div className="text-sm font-medium text-gray-500">Active Clients</div>
                                    <div className="text-3xl font-bold text-gray-900 mt-2">{analytics.active_clients_count}</div>
                                </div>
                            </div>
                        ) : (
                            <div className="bg-white rounded-lg shadow-md p-12 text-center">
                                <i className="fas fa-chart-line text-4xl text-purple-600 mb-4"></i>
                                <p className="text-gray-600">Loading analytics...</p>
                            </div>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
};

// ==================== MAIN APP ====================

const App = () => {
    const [auth, setAuth] = useState(loadAuth());

    const handleLogin = (authData) => {
        setAuth(authData);
    };

    const handleLogout = () => {
        saveAuth(null);
        setAuth(null);
    };

    if (!auth) {
        return <Login onLogin={handleLogin} />;
    }

    return <Dashboard auth={auth} onLogout={handleLogout} />;
};

ReactDOM.render(<App />, document.getElementById("root"));
