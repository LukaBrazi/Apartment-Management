"use client";

import { Input } from "@/components/ui/input";
import { setSearchTerm } from "@/lib/redux/features/users/userSlice";
import { useAppDispatch, useAppSelector } from "@/lib/redux/hooks/typedHooks";
import { Search } from "lucide-react";
import React from "react";

const UsersSearch = () => {
	const dispatch = useAppDispatch();
	const searchTerm = useAppSelector((state) => state.user.searchTerm);

	return (
		<div className="relative">
			<Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-[--text-muted]" />
			<Input
				placeholder="Пошук за ім'ям, прізвищем або нікнеймом…"
				type="search"
				value={searchTerm}
				onChange={(e) => dispatch(setSearchTerm(e.target.value))}
				className="no-focus border-[--border] bg-[--bg-surface] pl-9 text-sm text-[--text-primary] placeholder:text-[--text-muted] focus:border-[--accent]"
			/>
		</div>
	);
};

export default UsersSearch;
