<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useAuthStore } from '../../stores/auth';
const authStore = useAuthStore();
import { Trash2, UserPlus, Shield, User as UserIcon } from 'lucide-vue-next';

interface User {
  id: number;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
}

const users = ref<User[]>([]);
const loading = ref(false);
const error = ref('');

// Form State
const showCreateForm = ref(false);
const newUser = ref({ username: '', password: '', role: 'user' });
const createLoading = ref(false);
const createError = ref('');

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const fetchUsers = async () => {
    loading.value = true;
    error.value = '';
    try {
        const res = await fetch(`${API_BASE}/users`, {
            headers: { 'Authorization': `Bearer ${authStore.token}` }
        });
        if (!res.ok) throw new Error("Failed to fetch users");
        users.value = await res.json();
    } catch (e: any) {
        error.value = e.message;
    } finally {
        loading.value = false;
    }
};

const createUser = async () => {
    createLoading.value = true;
    createError.value = '';
    try {
        const isSuperuser = newUser.value.role === 'admin';
        const res = await fetch(`${API_BASE}/users`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${authStore.token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: newUser.value.username,
                password: newUser.value.password,
                is_active: true,
                is_superuser: isSuperuser
            })
        });
        
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to create user");
        }
        
        await fetchUsers();
        showCreateForm.value = false;
        newUser.value = { username: '', password: '', role: 'user' };
    } catch (e: any) {
        createError.value = e.message;
    } finally {
        createLoading.value = false;
    }
};

onMounted(() => {
    fetchUsers();
});
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6 gap-4 flex-wrap">
        <div>
            <h3 class="text-lg font-medium text-slate-800">System Users</h3>
            <p class="text-slate-500 text-sm">Manage access and roles</p>
        </div>
        <button 
            @click="showCreateForm = !showCreateForm"
            class="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition"
        >
            <UserPlus :size="16" /> {{ showCreateForm ? 'Cancel' : 'Add User' }}
        </button>
    </div>
    
    <!-- Create Form -->
    <div v-if="showCreateForm" class="mb-6 bg-slate-50 p-4 rounded-lg border border-slate-200 animate-in fade-in slide-in-from-top-1">
        <h4 class="font-medium text-sm mb-3">New User Details</h4>
        <form @submit.prevent="createUser" class="flex flex-col gap-3 max-w-sm">
            <div>
                <input v-model="newUser.username" required class="w-full px-3 py-2 text-sm border border-slate-300 rounded focus:ring-1 focus:ring-blue-500 outline-none" placeholder="Username" />
            </div>
            <div>
                 <input v-model="newUser.password" type="password" required class="w-full px-3 py-2 text-sm border border-slate-300 rounded focus:ring-1 focus:ring-blue-500 outline-none" placeholder="Password" />
            </div>
            <div>
                 <select v-model="newUser.role" class="w-full px-3 py-2 text-sm border border-slate-300 rounded bg-white focus:ring-1 focus:ring-blue-500 outline-none">
                    <option value="user">Standard User</option>
                    <option value="admin">Administrator</option>
                 </select>
            </div>
            
            <div v-if="createError" class="text-red-600 text-xs">{{ createError }}</div>
            
            <button 
                type="submit" 
                :disabled="createLoading"
                class="mt-1 bg-slate-800 text-white py-1.5 text-sm rounded hover:bg-slate-700 disabled:opacity-50"
            >
                {{ createLoading ? 'Creating...' : 'Create User' }}
            </button>
        </form>
    </div>
    
    <!-- User List -->
    <div class="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <div v-if="loading" class="p-8 text-center text-slate-500 text-sm">Loading users...</div>
        <div v-else-if="error" class="p-8 text-center text-red-600 text-sm">{{ error }}</div>
        
        <table v-else class="w-full text-left border-collapse">
            <thead class="bg-slate-50 text-slate-500 text-xs uppercase font-semibold border-b border-slate-200">
                <tr>
                    <th class="px-4 py-3">User</th>
                    <th class="px-4 py-3">Role</th>
                    <th class="px-4 py-3">Status</th>
                    <th class="px-4 py-3 text-right">Actions</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
                <tr v-for="user in users" :key="user.id" class="hover:bg-slate-50/50">
                    <td class="px-4 py-3 flex items-center gap-3 font-medium text-slate-700 text-sm">
                        <div class="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center text-slate-500">
                            <Shield v-if="user.is_superuser" :size="12" />
                            <UserIcon v-else :size="12" />
                        </div>
                        {{ user.username }}
                    </td>
                    <td class="px-4 py-3 text-xs">
                        <span 
                            class="px-2 py-0.5 rounded-full font-medium border"
                            :class="user.is_superuser ? 'bg-purple-50 text-purple-600 border-purple-100' : 'bg-slate-50 text-slate-600 border-slate-200'"
                        >
                            {{ user.is_superuser ? 'Admin' : 'User' }}
                        </span>
                    </td>
                    <td class="px-4 py-3 text-xs">
                        <span 
                            class="px-2 py-0.5 rounded-full font-medium border"
                            :class="user.is_active ? 'bg-green-50 text-green-600 border-green-100' : 'bg-red-50 text-red-600 border-red-100'"
                        >
                            {{ user.is_active ? 'Active' : 'Inactive' }}
                        </span>
                    </td>
                    <td class="px-4 py-3 text-right">
                        <!-- Placeholder for actions (e.g. delete) -->
                        <span class="text-xs text-slate-300">No Actions</span>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
  </div>
</template>
