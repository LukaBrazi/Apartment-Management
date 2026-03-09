import { createSlice } from "@reduxjs/toolkit";

interface AuthState {
	isAuthenticated: boolean;
	isInitialized: boolean;
}

const initialState: AuthState = {
	isAuthenticated: false,
	isInitialized: false,
};

const authSlice = createSlice({
	name: "auth",
	initialState,
	reducers: {
		setAuth: (state) => {
			state.isAuthenticated = true;
			state.isInitialized = true;
		},
		setLogout: (state) => {
			state.isAuthenticated = false;
			state.isInitialized = true;
		},
	},
});

export const { setAuth, setLogout } = authSlice.actions;
export default authSlice.reducer;
