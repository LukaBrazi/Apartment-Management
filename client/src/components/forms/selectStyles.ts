const customStyles = {
	control: (provided: any, state: any) => ({
		...provided,
		backgroundColor: "var(--select-background-color)",
		borderColor: state.isFocused
			? "var(--select-border-hover-color)"
			: "var(--select-border-color)",
		borderRadius: "0.75rem",
		boxShadow: state.isFocused
			? "0 0 0 1px var(--select-border-hover-color)"
			: "none",
		color: "var(--select-text-color)",
		minHeight: "44px",
		"&:hover": {
			borderColor: "var(--select-border-hover-color)",
		},
	}),
	option: (provided: any, state: any) => ({
		...provided,
		backgroundColor: state.isSelected
			? "var(--select-option-selected-background-color)"
			: "var(--select-option-background-color)",
		color: state.isSelected ? "#ffffff" : "var(--select-option-text-color)",
		"&:hover": {
			backgroundColor: "var(--select-option-hover-background-color)",
		},
		cursor: "pointer",
	}),
	singleValue: (provided: any) => ({
		...provided,
		color: "var(--select-value-text-color)",
	}),
	menu: (provided: any) => ({
		...provided,
		backgroundColor: "var(--select-menu-background-color, #ffffff)",
		borderRadius: "0.75rem",
		border: "1px solid var(--select-border-color)",
		boxShadow: "0 4px 16px rgba(0,0,0,0.12)",
		overflow: "hidden",
	}),
	menuList: (provided: any) => ({
		...provided,
		padding: "4px",
	}),
	placeholder: (provided: any) => ({
		...provided,
		color: "var(--select-text-color)",
		opacity: 0.5,
	}),
	input: (provided: any) => ({
		...provided,
		color: "var(--select-text-color)",
	}),
};

export default customStyles;
